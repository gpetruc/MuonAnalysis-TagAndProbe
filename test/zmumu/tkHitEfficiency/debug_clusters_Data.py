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
process.siStripDigisRedone = EventFilter.SiStripRawToDigi.SiStripDigis_cfi.siStripDigis.clone(
    UnpackCommonModeValues = True,
)

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
        stripCommonMode = cms.InputTag("siStripDigisRedone","CommonMode"),
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
process.source.fileNames = [
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/04B93E10-4328-E611-A8CA-02163E0135D0.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/0AA8AD56-4328-E611-8758-02163E013975.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/0C60C3F9-4328-E611-9C46-02163E014340.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/1009B80A-4628-E611-9E6E-02163E014587.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/142DC033-1528-E611-AD43-02163E0137D5.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/14435014-4328-E611-B78C-02163E013713.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/14EC7CCA-4328-E611-A875-02163E01342C.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/16299419-4428-E611-9538-02163E01433F.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/1A57B62A-4328-E611-9D78-02163E01339F.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/1C644E74-4328-E611-997E-02163E014354.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/1E92C329-1628-E611-A001-02163E014266.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/2CC90B4C-4328-E611-9282-02163E01465A.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/32A5C5EA-4428-E611-9327-02163E014191.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/367BE367-4328-E611-86C5-02163E014405.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/481FBB1B-4328-E611-A8F0-02163E011B15.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/52EBCB16-4328-E611-9939-02163E0138C3.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/56D424B6-4428-E611-805D-02163E01471E.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/5A5A22FD-4328-E611-B3E9-02163E012543.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/5A7AE0F6-4328-E611-A876-02163E0136ED.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/5E4F7606-4328-E611-9928-02163E01196F.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/603AD708-4328-E611-A562-02163E01451A.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/60959422-4328-E611-8A1D-02163E011B6E.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/64E6FB01-4328-E611-BBC9-02163E011E84.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/66FDD364-4428-E611-AED4-02163E0141B2.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/68616BB3-1128-E611-9D3F-02163E0139BF.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/721A82A7-1B28-E611-9EFE-02163E0133CD.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/7A833D08-4328-E611-B1CC-02163E013421.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/7A9ED9F5-4328-E611-AD64-02163E0144F4.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/7C394588-4428-E611-BAEB-02163E012828.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/82995B1C-4328-E611-A5E6-02163E0120F3.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/8A78292B-4328-E611-B9D1-02163E011DA7.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/900F67CD-4328-E611-8AB8-02163E01391D.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/9C450828-4728-E611-93EB-02163E014728.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/A42C5BB2-4328-E611-8FDF-02163E01343F.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/A4AB0516-4328-E611-95B7-02163E0135FD.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/AC797755-4328-E611-BF2B-02163E013975.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/AC804B11-4328-E611-89A0-02163E011B16.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/AE25780F-4428-E611-9839-02163E0143A2.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/B0ABCFDF-1B28-E611-A398-02163E0133C6.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/B617198D-4428-E611-A602-02163E01411C.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/B6674869-4328-E611-9E27-02163E013821.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/BA0CBFBC-4328-E611-8DBE-02163E014549.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/BA60E909-1928-E611-AB66-02163E011CF6.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/BAB34C38-1B28-E611-8352-02163E01466D.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/BE047F27-1D28-E611-8B41-02163E011CDE.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/C40EB2D8-1428-E611-B910-02163E012584.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/C6C2452E-4328-E611-80F2-02163E01422C.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/CAC78512-4328-E611-8DDC-02163E01414D.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/CCC83028-4328-E611-B3EA-02163E0137B0.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/D05F95CB-1828-E611-96F3-02163E012628.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/D88E7755-4328-E611-919E-02163E013975.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/DCF7D426-4328-E611-90E2-02163E012492.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/DE08438B-4428-E611-9BD8-02163E0141F5.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/E03633E4-4328-E611-9D80-02163E01341C.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/E08C5CFB-4328-E611-B9B5-02163E01338B.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/E2912B0D-4328-E611-92EF-02163E0120B5.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/F0BEB82B-4328-E611-A8BD-02163E014752.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/F4F7F303-4328-E611-8B9E-02163E01245C.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/F62A6796-4428-E611-A4AB-02163E013695.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/314/00000/FA086044-1B28-E611-8BDD-02163E011990.root',
]
