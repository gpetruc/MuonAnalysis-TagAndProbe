
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
#include "DataFormats/SiStripCluster/interface/SiStripClusterTools.h"
#include "DataFormats/TrackerRecHit2D/interface/TrackerSingleRecHit.h"

namespace {
    static std::vector<std::string> sDETS{ "", "TIB", "TID", "TOB", "TEC" };
    static std::vector<unsigned>    iDETS{ 0,   3,      4,     5,     6   };
}

class ClusterShapeFilterStudies : public edm::EDProducer {
public:
  explicit ClusterShapeFilterStudies(const edm::ParameterSet&);
  ~ClusterShapeFilterStudies();

private:
  virtual void produce(edm::Event&, const edm::EventSetup&);

  struct DetAndCharge { 
        uint32_t det; float charge; 
        DetAndCharge(uint32_t adet, float acharge) : det(adet), charge(acharge) {} 
        bool operator<(const DetAndCharge &other) const { return charge < other.charge; } 
  };
  std::vector<DetAndCharge> hitsOnTrack(const reco::Track &track, double estimateCut=9e9) const ;

  // ----------member data ---------------------------
  const edm::EDGetTokenT<edm::View<reco::Muon>> probes_;    
  double estimateCut_;
  /// Track Transformer
  TrackTransformer refitter_;

  /// Store extra information in a ValueMap
  template<typename Hand, typename T>
  void storeMap(edm::Event &iEvent, 
  const Hand & handle,
  const std::vector<T> & values,
  const std::string    & label) const ;
};

//
// constructors and destructor
//
ClusterShapeFilterStudies::ClusterShapeFilterStudies(const edm::ParameterSet& iConfig):
probes_(consumes<edm::View<reco::Muon>>(iConfig.getParameter<edm::InputTag>("probes"))),
estimateCut_(iConfig.getParameter<double>("estimateCut")),
refitter_(iConfig)
{
  for (unsigned int i = 0, n = sDETS.size(); i < n; ++i) { 
      produces<edm::ValueMap<float> >("median"+sDETS[i]);
      produces<edm::ValueMap<float> >("byCharge0"+sDETS[i]);
      produces<edm::ValueMap<float> >("byCharge1"+sDETS[i]);
      produces<edm::ValueMap<float> >("byCharge2"+sDETS[i]);
  }
}


ClusterShapeFilterStudies::~ClusterShapeFilterStudies()
{
}

void
ClusterShapeFilterStudies::produce(edm::Event& iEvent, const edm::EventSetup& iSetup)
{
  using namespace edm;

  // read input
  Handle<View<reco::Muon> > probes;
  iEvent.getByToken(probes_, probes);

  if (!probes->empty()) refitter_.setServices(iSetup);

  unsigned int n = probes->size();
  std::vector<float> byCharge[5][3];
  std::vector<float> median[5];
  for (unsigned int idet = 0; idet < 5; ++idet) {
      median[idet] = std::vector<float>(n,0);
      for (unsigned int i = 0; i < 3; ++i) {
          byCharge[idet][i] = std::vector<float>(n,0);
      }
  }

  for (unsigned int i = 0; i < n; ++i) {
      const reco::Muon &mu = (*probes)[i];
      if (mu.innerTrack().isNull()) continue;
      std::vector<DetAndCharge> hitsAll = hitsOnTrack(*mu.innerTrack(), estimateCut_);
      std::sort(hitsAll.begin(), hitsAll.end());
      for (int idet = 0; idet < 5; ++idet) {
          std::vector<DetAndCharge> hits;
          for (auto & h : hits) { 
            if (idet == 0 || h.det == iDETS[idet]) hits.push_back(h);
         }
          median[idet][i] = hits.empty() ? 9999. : (
                  hits.size() % 2 == 1 ? hits[(hits.size()+1)/2].charge 
                  : 0.5*(hits[hits.size()/2].charge + hits[hits.size()/2+1].charge));
          byCharge[idet][0][i] = (hits.size() > 0 ? hits[0].charge : 999999.);
          byCharge[idet][1][i] = (hits.size() > 1 ? hits[1].charge : 999999.);
          byCharge[idet][2][i] = (hits.size() > 2 ? hits[2].charge : 999999.);
      } 
  }

  for (int idet = 0; idet < 5; ++idet) {
      storeMap(iEvent, probes, median[idet], "median"+sDETS[idet]);
      storeMap(iEvent, probes, byCharge[idet][0], "byCharge0"+sDETS[idet]);
      storeMap(iEvent, probes, byCharge[idet][1], "byCharge1"+sDETS[idet]);
      storeMap(iEvent, probes, byCharge[idet][2], "byCharge2"+sDETS[idet]);
  }
}

std::vector<ClusterShapeFilterStudies::DetAndCharge>
ClusterShapeFilterStudies::hitsOnTrack(const reco::Track &track, double estimateCut) const 
{
    std::vector<DetAndCharge> ret;
    std::vector<Trajectory> traj  = refitter_.transform(track);
    if (traj.size() != 1) return ret; 
    for (const auto &tm : traj.front().measurements()) {
        if (tm.recHit().get() && tm.recHit()->isValid() && tm.updatedState().isValid() && tm.estimate() < estimateCut) {
            const auto &tsos = tm.updatedState();
            const TrackerSingleRecHit *hit = dynamic_cast<const TrackerSingleRecHit *>(&tm.recHitR());
            if (hit == 0 || hit->omniCluster().isPixel()) continue;
            int subdet = tm.recHitR().geographicalId().subdetId();
            float charge =  siStripClusterTools::chargePerCM(hit->geographicalId(), hit->stripCluster(), tsos.localParameters());
            if (charge < 1945.0) std::cout << "Low charge hit on sub " << subdet << ", charge " << charge << ", chi2 " << tm.estimate() << std::endl;
            //std::cout << "subdet " << tm.recHitR().geographicalId().subdetId() << ", hit: " << typeid(tm.recHitR()).name() << ", charge " << charge << ", sub: " << subdet << std::endl;
            ret.push_back(DetAndCharge(subdet,charge)); 
        }
    }
    return ret;
}

template<typename Hand, typename T>
void
ClusterShapeFilterStudies::storeMap(edm::Event &iEvent,
const Hand & handle,
const std::vector<T> & values,
const std::string    & label) const {
  using namespace edm; using namespace std;
  auto_ptr<ValueMap<T> > valMap(new ValueMap<T>());
  typename edm::ValueMap<T>::Filler filler(*valMap);
  filler.insert(handle, values.begin(), values.end());
  filler.fill();
  iEvent.put(valMap, label);
}

//define this as a plug-in
DEFINE_FWK_MODULE(ClusterShapeFilterStudies);
