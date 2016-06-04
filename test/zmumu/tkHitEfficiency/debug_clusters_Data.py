import FWCore.ParameterSet.Config as cms

process = cms.Process("TagProbe")

process.load('Configuration.StandardSequences.Services_cff')
process.load('FWCore.MessageService.MessageLogger_cfi')
process.options   = cms.untracked.PSet( wantSummary = cms.untracked.bool(True) )
process.MessageLogger.cerr.FwkReport.reportEvery = 100
process.MessageLogger.suppressError = cms.untracked.vstring("patTriggerFull")
process.source = cms.Source("PoolSource", 
    fileNames = cms.untracked.vstring('/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/E03633E4-4328-E611-9D80-02163E01341C.root')
)
JSON = '/afs/cern.ch/cms/CAF/CMSCOMM/COMM_DQM/certification/Collisions16/13TeV/DCSOnly/json_DCSONLY.txt'
import FWCore.PythonUtilities.LumiList as LumiList
process.source.lumisToProcess = LumiList.LumiList(filename = JSON).getVLuminosityBlockRange()

process.maxEvents = cms.untracked.PSet( input = cms.untracked.int32(-1) )    

process.load('Configuration.StandardSequences.GeometryRecoDB_cff')
process.load('Configuration.StandardSequences.MagneticField_cff')
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_condDBv2_cff')
process.load("Configuration.StandardSequences.Reconstruction_cff")
import EventFilter.SiStripRawToDigi.SiStripDigis_cfi
process.siStripDigisRedone = EventFilter.SiStripRawToDigi.SiStripDigis_cfi.siStripDigis.clone()

from Configuration.AlCa.GlobalTag import GlobalTag
process.GlobalTag = GlobalTag(process.GlobalTag, '80X_dataRun2_Express_v6', '')
#process.GlobalTag = GlobalTag(process.GlobalTag, '80X_dataRun2_Prompt_v8', '')

#process.load("HLTrigger.HLTfilters.triggerResultsFilter_cfi")
process.triggerResultsFilter = cms.EDFilter("TriggerResultsFilter",
    daqPartitions = cms.uint32(1),
    hltResults = cms.InputTag("TriggerResults","","HLT"),
    l1tIgnoreMask = cms.bool(False),
    l1tResults = cms.InputTag(""),
    l1techIgnorePrescales = cms.bool(False),
    throw = cms.bool(True),
    triggerConditions = cms.vstring('HLT_IsoMu20_v*')
)

process.preselMu = cms.EDFilter("MuonSelector",
    src = cms.InputTag("muons"),
    cut = cms.string("track.isNonnull && pt > 10"),
    filter = cms.bool(True)
)
process.preselPairs = cms.EDProducer("CandViewShallowCloneCombiner",
    cut = cms.string('60 < mass < 140'),
    decay = cms.string('preselMu@+ preselMu@-')
)
process.onePreselPair = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("preselPairs"), minNumber = cms.uint32(1))
process.preselSeq = cms.Sequence(process.preselMu + process.preselPairs + process.onePreselPair)

process.load("MuonAnalysis.MuonAssociators.patMuonsWithTrigger_cff")
process.muonMatchHLTL3.maxDeltaR = 0.1
from MuonAnalysis.MuonAssociators.patMuonsWithTrigger_cff import *

from MuonAnalysis.TagAndProbe.common_variables_cff import *
process.load("MuonAnalysis.TagAndProbe.common_modules_cff")

process.tagMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("patMuonsWithTrigger"),
    cut = cms.string("pt > 20 && numberOfMatchedStations >= 2"+
                     " && !triggerObjectMatchesByPath('HLT_IsoMu20_v*',1,0).empty()"+
                     " && pfIsolationR04().sumChargedHadronPt/pt < 0.2"),
)
process.oneTag  = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("tagMuons"), minNumber = cms.uint32(1))

process.probeMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("patMuonsWithTrigger"),
    cut = cms.string("pt > 10 && numberOfMatchedStations >= 1 && innerTrack.isNonnull && innerTrack.hitPattern.numberOfLostStripHits('TRACK_HITS') > 0 && abs(eta) < 1.0"), 
)
process.tpPairs = cms.EDProducer("CandViewShallowCloneCombiner",
    cut = cms.string('60 < mass < 140'),
    decay = cms.string('tagMuons@+ probeMuons@-')
)
process.onePair = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("tpPairs"), minNumber = cms.uint32(1))

process.clusterInfo = cms.EDProducer("DebugTkHits",
        pairs = cms.InputTag("tpPairs"),
        stripClusters = cms.InputTag("siStripClusters"),
        stripDigis = cms.InputTag("siStripDigisRedone","ZeroSuppressed"),
        tracker = cms.InputTag("MeasurementTrackerEvent"),
        layersToDebug = cms.untracked.vstring("TOB1"),
        # configuraton for refitter
        DoPredictionsOnly = cms.bool(False),
        #KeepInvalidHits = cms.bool(True),
        Fitter = cms.string('KFFitterForRefitInsideOut'),
        TrackerRecHitBuilder = cms.string('WithAngleAndTemplate'),
        Smoother = cms.string('KFSmootherForRefitInsideOut'),
        MuonRecHitBuilder = cms.string('MuonRecHitBuilder'),
        RefitDirection = cms.string('alongMomentum'),
        RefitRPCHits = cms.bool(True),
        Propagator = cms.string('SmartPropagatorAnyRKOpposite'),
        #Propagators
        PropagatorAlong = cms.string("RungeKuttaTrackerPropagator"),
        PropagatorOpposite = cms.string("RungeKuttaTrackerPropagatorOpposite"),
        SiStripQuality = cms.string(''),
)

process.tagAndProbe = cms.Path( 
    process.triggerResultsFilter +
    process.preselSeq  +
    process.patMuonsWithTriggerSequence +
    process.tagMuons +
    process.oneTag     +
    process.probeMuons +
    process.tpPairs    +
    process.onePair    +
    process.MeasurementTrackerEvent +
    process.siStripDigisRedone +
    process.clusterInfo 
)

process.TFileService = cms.Service("TFileService", fileName = cms.string("tnpZ_Data_Express.root"))
