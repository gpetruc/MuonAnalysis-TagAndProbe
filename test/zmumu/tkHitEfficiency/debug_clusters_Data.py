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
process.GlobalTag = GlobalTag(process.GlobalTag, '80X_dataRun2_Express_v10', '')
#process.GlobalTag = GlobalTag(process.GlobalTag, '80X_dataRun2_Prompt_v8', '')

#process.load("HLTrigger.HLTfilters.triggerResultsFilter_cfi")
process.triggerResultsFilter = cms.EDFilter("TriggerResultsFilter",
    daqPartitions = cms.uint32(1),
    hltResults = cms.InputTag("TriggerResults","","HLT"),
    l1tIgnoreMask = cms.bool(False),
    l1tResults = cms.InputTag(""),
    l1techIgnorePrescales = cms.bool(False),
    throw = cms.bool(True),
    triggerConditions = cms.vstring('HLT_IsoMu20_v*','HLT_IsoMu24_v*')
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
                     " && !(triggerObjectMatchesByPath('HLT_IsoMu20_v*',1,0).empty() && triggerObjectMatchesByPath('HLT_IsoMu24_v*',1,0).empty())"+
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

process.out = cms.OutputModule("PoolOutputModule",
    fileName = cms.untracked.string("debug_Zmm_lostHits.root"),
    outputCommands = cms.untracked.vstring("keep *", "drop *_*_*_TagProbe")
    SelectEvents = cms.untracked.PSet(SelectEvents = cms.vstring("tagAndProbe")),
)
#uncomment to skim the selected events
#process.end = cms.EndPath(process.out)

# this below probably not needed
#process.TFileService = cms.Service("TFileService", fileName = cms.string("tnpZ_Data_Express.root"))
process.source.fileNames = [
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/187D8BE5-7744-E611-92F8-02163E01449C.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/18D6D814-6144-E611-916A-02163E011918.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/18DF9AB7-7044-E611-B77F-02163E0142E7.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/1A3E9BD4-6044-E611-9499-02163E01346C.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/1A7AEB46-7644-E611-8125-02163E014516.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/1C206E85-6244-E611-BBC7-02163E01411A.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/1C2B4FB7-6244-E611-A862-02163E0145C3.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/1E41204C-7B44-E611-8510-02163E0138F8.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/1EEDC171-6244-E611-B69E-02163E0146B6.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/20026E1C-6344-E611-93EC-02163E014244.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/22DB237D-6244-E611-8B9C-02163E011E73.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/24C55FEC-7544-E611-A3FA-02163E013545.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/262A4C7B-6144-E611-B33C-02163E0137FB.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/28BECE0F-7844-E611-BE4E-02163E013617.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/28D4C09F-6244-E611-B787-02163E013649.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/28E4ACA4-7544-E611-823C-02163E013744.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/2E7CC720-7844-E611-9448-02163E0143F7.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/3086518A-7844-E611-97C5-02163E013647.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/30E0167D-6144-E611-BFBF-02163E011A71.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/328F1EC8-6244-E611-9362-02163E01460B.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/3471C6F5-8044-E611-81A4-02163E0145E2.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/34E80356-6244-E611-817B-02163E014278.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/36B01F48-7144-E611-9EF7-02163E0140D4.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/3A2B443B-8044-E611-92A6-02163E011A2F.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/3A7DC5A2-3B44-E611-B3D3-02163E01190C.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/3CE69CDD-7744-E611-9426-02163E011837.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/4034D09D-7844-E611-BC56-02163E011E55.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/42627346-6144-E611-A2BE-02163E0129F1.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/42BC5EC5-6044-E611-9A0B-02163E0135EF.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/42F08DA8-6044-E611-BCF3-02163E012A77.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/46389633-7744-E611-BEC0-02163E01376A.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/48C0585B-6244-E611-BBB7-02163E0133BB.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/4C028E1B-6344-E611-9D7D-02163E0142F9.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/4C9D6DD9-7544-E611-A446-02163E011E55.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/4CA0D2C3-7844-E611-9969-02163E014523.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/4EA37673-6144-E611-9CAE-02163E0127F4.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/4EABAE46-6244-E611-8DC0-02163E01396E.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/52A0796E-6244-E611-B730-02163E013855.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/586633E4-7A44-E611-A918-02163E01477D.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/586E3158-7944-E611-BCA5-02163E013758.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/605119AE-7844-E611-884C-02163E0141C3.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/62266C87-6144-E611-A36C-02163E012205.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/62D87868-7144-E611-AA61-02163E01267E.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/644EC0E9-6244-E611-82F6-02163E0134AF.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/66F28151-6144-E611-B93D-02163E011A47.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/6A201C9A-7444-E611-81AB-02163E013529.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/6A488AA8-7044-E611-98AD-02163E013744.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/6C3F50FD-7544-E611-B75E-02163E013862.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/6E2C4B8C-7A44-E611-81FE-02163E011B8C.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/7027F0E2-7744-E611-BDF5-02163E0141AC.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/707C3DAC-6144-E611-8821-02163E0146F4.root',
        '/store/express/Run2016D/ExpressPhysics/FEVT/Express-v2/000/276/495/00000/70B1D5AA-3B44-E611-8B91-02163E012AE4.root',
]
