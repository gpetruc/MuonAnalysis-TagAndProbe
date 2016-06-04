
// system include files
#include <memory>
#include <cmath>

// user include files
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/EDProducer.h"

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/ESHandle.h"

#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ServiceRegistry/interface/Service.h"

#include "DataFormats/Common/interface/ValueMap.h"
#include "DataFormats/MuonReco/interface/Muon.h"
#include "TrackingTools/TrackRefitter/interface/TrackTransformer.h"
#include "TrackingTools/PatternTools/interface/Trajectory.h"
#include "DataFormats/Common/interface/DetSetVector.h"
#include "DataFormats/SiStripDigi/interface/SiStripDigi.h"
#include "DataFormats/SiStripDigi/interface/SiStripRawDigi.h"
#include "DataFormats/SiStripCluster/interface/SiStripCluster.h"
#include "DataFormats/SiPixelCluster/interface/SiPixelCluster.h"
#include "DataFormats/SiStripCluster/interface/SiStripClusterTools.h"
#include "DataFormats/TrackerRecHit2D/interface/TrackerSingleRecHit.h"
#include "DataFormats/TrackerCommon/interface/TrackerTopology.h"
#include "Geometry/Records/interface/TrackerTopologyRcd.h"
#include "RecoTracker/MeasurementDet/interface/MeasurementTrackerEvent.h"
#include "Geometry/TrackerGeometryBuilder/interface/GluedGeomDet.h"
#include "Geometry/CommonTopologies/interface/Topology.h"
#include "TrackingTools/GeomPropagators/interface/Propagator.h"
#include "TrackingTools/Records/interface/TrackingComponentsRecord.h"
#include "CalibFormats/SiStripObjects/interface/SiStripQuality.h"
#include "CalibTracker/Records/interface/SiStripQualityRcd.h"

namespace {
    static std::vector<std::string> sDETS{ "", "PXB", "PXF", "TIB", "TID", "TOB", "TEC" };
    static std::vector<unsigned>    iDETS{ 0,   1,    2,     3,      4,     5,     6   };
    static std::vector<unsigned>    iLAYS{ 0,   3,    2,     4,      3,     6,     9   };
    static std::vector<std::string> sLAYS{ "0", "1", "2", "3", "4", "5", "6", "7", "8", "9" };
}

class DebugTkHits : public edm::EDProducer {
public:
  explicit DebugTkHits(const edm::ParameterSet&);
  ~DebugTkHits();

private:
  virtual void produce(edm::Event&, const edm::EventSetup&);

  // ----------member data ---------------------------
  const edm::EDGetTokenT<edm::View<reco::Candidate>> pairs_;    
  const edm::EDGetTokenT<edmNew::DetSetVector<SiStripCluster>> stripClusterLabel_;
  const edm::EDGetTokenT<edm::DetSetVector<SiStripDigi>> stripDigiLabel_;
  const edm::EDGetTokenT<edm::DetSetVector<SiStripRawDigi>> stripRawDigiLabel_;
  edm::EDGetTokenT<MeasurementTrackerEvent> tracker_;
  /// Layers to debug
  std::vector<std::string> layersToDebug_;
  /// Track Transformer
  TrackTransformer refitter_;
  std::string propagator_, propagatorOpposite_;
  std::string stripQualityLabel_;

  edm::ESHandle<TrackerTopology> theTrkTopo;
  edm::ESHandle<Propagator> thePropagator, thePropagatorOpposite;
  edm::ESHandle<SiStripQuality> theStripQuality;

  void bar(int i, int scale, int sat=254) {
    std::cout << std::setw(4) << i << " |" ;
    for (int k = 0; k < (i+scale/2)/scale; ++k) std::cout << "=";
    if (i >= sat) std::cout << "X";
    std::cout << std::endl; 
  }
};

//
// constructors and destructor
//
DebugTkHits::DebugTkHits(const edm::ParameterSet& iConfig):
    pairs_(consumes<edm::View<reco::Candidate>>(iConfig.getParameter<edm::InputTag>("pairs"))),
    stripClusterLabel_(consumes<edmNew::DetSetVector<SiStripCluster>>(iConfig.getParameter<edm::InputTag>("stripClusters"))),
    stripDigiLabel_(consumes<edm::DetSetVector<SiStripDigi>>(iConfig.getParameter<edm::InputTag>("stripDigis"))),
    //stripRawDigiLabel_(consumes<edm::DetSetVector<SiStripRawDigi>>(iConfig.getParameter<edm::InputTag>("stripRawDigis"))),
    tracker_(consumes<MeasurementTrackerEvent>(iConfig.getParameter<edm::InputTag>("tracker"))),
    layersToDebug_(iConfig.getUntrackedParameter<std::vector<std::string>>("layersToDebug", std::vector<std::string>())),
    refitter_(iConfig),
    propagator_(iConfig.getParameter<std::string>("PropagatorAlong")),
    propagatorOpposite_(iConfig.getParameter<std::string>("PropagatorOpposite")),
    stripQualityLabel_(iConfig.getParameter<std::string>("SiStripQuality"))
{
}


DebugTkHits::~DebugTkHits()
{
}

void
DebugTkHits::produce(edm::Event& iEvent, const edm::EventSetup& iSetup)
{
  using namespace edm;

  // read input
  Handle<View<reco::Candidate> > pairs;
  iEvent.getByToken(pairs_, pairs);

  if (pairs->empty()) return;

  iSetup.get<TrackerTopologyRcd>().get(theTrkTopo);
  refitter_.setServices(iSetup);

  iSetup.get<TrackingComponentsRecord>().get(propagator_, thePropagator);
  iSetup.get<TrackingComponentsRecord>().get(propagatorOpposite_, thePropagatorOpposite);
  iSetup.get<SiStripQualityRcd>().get(stripQualityLabel_, theStripQuality);
  //std::stringstream sss; theStripQuality->printDebug(sss); std::cout << sss.str() << std::endl;

  edm::Handle<edmNew::DetSetVector<SiStripCluster> > stripC; 
  iEvent.getByToken(stripClusterLabel_, stripC); 
  edm::Handle<edm::DetSetVector<SiStripDigi> > stripD; 
  iEvent.getByToken(stripDigiLabel_, stripD); 

  Handle<MeasurementTrackerEvent> tracker;
  iEvent.getByToken(tracker_, tracker);


  for (const reco::Candidate & pair : *pairs) {
      const reco::Muon &mu = dynamic_cast<const reco::Muon &>(*pair.daughter(1)->masterClone());
      if (mu.innerTrack().isNull()) continue;
      const reco::Track & mutk = *mu.innerTrack();
      std::cout << "Muon with pt " << mu.pt() << " eta " << mu.eta() << 
                        ", found hits: " << mutk.found() <<
                        ", lost hits: " << mutk.hitPattern().numberOfLostStripHits(reco::HitPattern::TRACK_HITS) << std::endl;
      int nhits = mutk.recHitsSize();
      std::vector<Trajectory> traj  = refitter_.transform(mutk);
      if (traj.size() != 1) continue; 
      const TrackingRecHit *invalid = nullptr; DetId previous, next;
      for (int i = 1; i < nhits; ++i) {
        const TrackingRecHit *hit = &* mutk.recHit(i);
        if (hit->getType() == TrackingRecHit::missing) { 
            invalid = hit;
            for (int j = i-1; j >= 0; --j) { 
                hit = &* mutk.recHit(j);
                if (hit->isValid()) previous = hit->geographicalId();
            }
            for (int j = i+1; j < nhits; ++j) {
                hit = &* mutk.recHit(j);
                if (hit->isValid()) next = hit->geographicalId();
            }
            break;
        }
      }
      if (invalid == nullptr || previous.rawId() == 0 || next.rawId() == 0) continue;
      DetId where =  invalid->geographicalId();
      int subdet = where.subdetId(), layer = theTrkTopo->layer(where);
      if (!layersToDebug_.empty()) {
          if (std::find(layersToDebug_.begin(), layersToDebug_.end(), sDETS[subdet]+sLAYS[layer]) == layersToDebug_.end()) {
              continue;
          }
      }
      std::cout << "Lost hit on " << sDETS[subdet] << layer << ", detid " << where() << ", previous hit on " << previous() << ", next on " << next()<< std::endl;
      MeasurementDetWithData mdet = tracker->idToDet(where);
      const GeomDet &gdet = mdet.fastGeomDet();
      std::cout << "Lost hit det is a " << typeid(mdet.mdet()).name() << ", geom " << typeid(gdet).name() << std::endl;
      std::vector<const GeomDet *> gdets;
      if (typeid(gdet) == typeid(GluedGeomDet)) {
        gdets.push_back((static_cast<const GluedGeomDet &>(gdet)).monoDet());
        gdets.push_back((static_cast<const GluedGeomDet &>(gdet)).stereoDet());
      } else {
        gdets.push_back(&gdet);
      }
      TrajectoryStateOnSurface tsosBefore, tsosAfter;
      for (const auto &tm : traj.front().measurements()) {
          if (tm.recHit().get() && tm.recHitR().isValid()) {
              if (tm.recHitR().geographicalId() == previous) {
                  tsosBefore = tm.updatedState().isValid() ? tm.updatedState() : tm.forwardPredictedState();
              } else if (tm.recHitR().geographicalId() == next) {
                  tsosAfter = tm.updatedState().isValid() ? tm.updatedState() : tm.backwardPredictedState();
              }
          }
      }
      for (const GeomDet *det : gdets) {
          where = det->geographicalId(); mdet = tracker->idToDet(where);
          std::cout << "Analyzing module at " << where() << ", isActive? " << mdet.isActive() << std::endl;
          float utraj = 0, uerr = 0; bool pred = false, hascluster = false, hasdigi = false, anycluster = false, anydigi = false;
          if (tsosBefore.isValid()) {
             TrajectoryStateOnSurface tsos = thePropagator->propagate(tsosBefore, det->surface());
             if (tsos.isValid()) {  
                pred = true;
                utraj = det->topology().measurementPosition( tsos.localPosition() ).x();
                uerr  = std::sqrt( det->topology().measurementError( tsos.localPosition(), tsos.localError().positionError() ).uu() ); 
                std::cout << "  Searching around strip " << utraj << " +/- " << uerr << "    APV: " << utraj/128 << std::endl;
             } else {
                std::cout << "  Failed to propagate??" << std::endl;
             }
          }
          if (!mdet.isActive()) {
            std::cout << "  Detector is inactive" << std::endl;
            continue;
          }
          std::cout << "  Bad components on the detector" << std::endl;
          std::cout << "  APVs (or fibers): ";
          for (unsigned int iapv = 0; iapv < 5; ++iapv) {
            if (theStripQuality->IsApvBad(where(), iapv) || theStripQuality->IsFiberBad(where(), iapv/2)) std::cout << iapv << " " ;
          } 
          std::cout << std::endl;
          std::cout << "  Strips: ";
          SiStripQuality::Range range = theStripQuality->getRange(where());
          for (auto strip = range.first; strip < range.second; ++strip) std::cout << (*strip) << " " ;
          std::cout << std::endl;
          auto cl_iter = stripC->find(where);
          if (cl_iter == stripC->end()) {
            std::cout << "  ... no strip clusters on this detid" << std::endl;
          } else {
            edmNew::DetSet<SiStripCluster> clusters = *cl_iter;
            for (const SiStripCluster &cluster : clusters) {
                std::cout << "  Cluster of " << cluster.amplitudes().size() << " strips: " << std::endl;
                const std::vector<uint8_t> & amps = cluster.amplitudes();
                for (unsigned int s = cluster.firstStrip(), i = 0, e  = amps.size(); i < e; ++s, ++i) {  
                    std::cout << "   " << std::setw(4) << s << " | " << (s/128) << " | "; bar(amps[i], 2);
                    if (pred && std::abs(s-utraj) < 5) { hascluster = true; anycluster = true; }
                    if (pred && (s/128) == floor(utraj/128)) anycluster = true;
                }
            }
          }
          auto di_iter = stripD->find(where);
          if (di_iter == stripD->end()) {
              std::cout << "  ... no strip digis on this detid" << std::endl;
          } else {
              std::cout << "  Digis on this detid" << std::endl;
              const edm::DetSet<SiStripDigi> & digis = *di_iter;
              for (unsigned int idigi = 0, ndigi = digis.size(); idigi < ndigi; ++idigi) {
                  if (idigi > 0 && (digis[idigi].strip() > digis[idigi-1].strip()+1)) std::cout << "      ---------------------" << std::endl;
                  std::cout << "   " << std::setw(4) << digis[idigi].strip() << " | " << (digis[idigi].strip()/128) << " | "; bar(digis[idigi].adc(), 4, 1024);
                  if (pred && std::abs(digis[idigi].strip()-utraj) < 5) { hasdigi = true; anydigi = true; }
                  if (pred && (digis[idigi].strip()/128) == floor(utraj/128)) anydigi = true;
              }
          }
          if (pred) {
             std::cout << "  Summary: " << ( hascluster  ? " cluster" : (anycluster ? " " : " no-clusters")) << 
                                          ( hasdigi  ? " digi" : (anydigi ? " " : " no-digis")) << std::endl;
          }
      }
      for (const auto &tm : traj.front().measurements()) {
          if (tm.recHit().get() && !tm.recHit()->isValid()) {
              DetId where =  tm.recHitR().geographicalId();
              int subdet = where.subdetId(), layer = theTrkTopo->layer(where);
              if (!layersToDebug_.empty()) {
                if (std::find(layersToDebug_.begin(), layersToDebug_.end(), sDETS[subdet]+sLAYS[layer]) == layersToDebug_.end()) {
                    continue;
                }
              }
              std::cout << " missing hit on " << sDETS[subdet] << " layer " << layer << " type = " << tm.recHitR().getType() << ", detid " << where() << std::endl;
          }
      }
  } 
}


//define this as a plug-in
DEFINE_FWK_MODULE(DebugTkHits);
