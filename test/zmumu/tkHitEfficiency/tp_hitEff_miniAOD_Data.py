import FWCore.ParameterSet.Config as cms

process = cms.Process("TagProbe")

process.load('Configuration.StandardSequences.Services_cff')
process.load('FWCore.MessageService.MessageLogger_cfi')
process.options   = cms.untracked.PSet( wantSummary = cms.untracked.bool(True) )
process.MessageLogger.cerr.FwkReport.reportEvery = 100
process.source = cms.Source("PoolSource", 
    fileNames = cms.untracked.vstring('/store/data/Run2016B/SingleMuon/MINIAOD/PromptReco-v2/000/274/200/00000/5C7EB03D-0928-E611-9C73-02163E01342D.root')
)
JSON = '/afs/cern.ch/cms/CAF/CMSCOMM/COMM_DQM/certification/Collisions16/13TeV/DCSOnly/json_DCSONLY.txt'
import FWCore.PythonUtilities.LumiList as LumiList
process.source.lumisToProcess = LumiList.LumiList(filename = JSON).getVLuminosityBlockRange()

process.maxEvents = cms.untracked.PSet( input = cms.untracked.int32(-1) )    

process.load('Configuration.StandardSequences.GeometryRecoDB_cff')
process.load('Configuration.StandardSequences.MagneticField_cff')
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_condDBv2_cff')
process.load("Configuration.StandardSequences.Reconstruction_cff")

from Configuration.AlCa.GlobalTag import GlobalTag
process.GlobalTag = GlobalTag(process.GlobalTag, '80X_dataRun2_Express_v6', '')

process.triggerResultsFilter = cms.EDFilter("TriggerResultsFilter",
    daqPartitions = cms.uint32(1),
    hltResults = cms.InputTag("TriggerResults","","HLT"),
    l1tIgnoreMask = cms.bool(False),
    l1tResults = cms.InputTag(""),
    l1techIgnorePrescales = cms.bool(False),
    throw = cms.bool(True),
    triggerConditions = cms.vstring('HLT_IsoMu20_v*')
)

process.preselMu = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("slimmedMuons"),
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
useExistingPATMuons(process, "slimmedMuons")

from PhysicsTools.PatAlgos.tools.helpers import massSearchReplaceAnyInputTag
process.globalReplace("patTriggerFull", cms.EDProducer("PATTriggerObjectStandAloneUnpacker",
    triggerResults =  cms.InputTag("TriggerResults","","HLT"),
    patTriggerObjectsStandAlone = cms.InputTag("selectedPatTrigger"),
))

from MuonAnalysis.TagAndProbe.common_variables_cff import *
del AllVariables.l1pt
del AllVariables.l1q
del AllVariables.l1dr
process.load("MuonAnalysis.TagAndProbe.common_modules_cff")
process.nverticesModule.objects = "offlineSlimmedPrimaryVertices"

process.tagMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("patMuonsWithTrigger"),
    cut = cms.string("pt > 20 && numberOfMatchedStations >= 2"+
                     " && !triggerObjectMatchesByCollection('hltL3MuonCandidates').empty()"+
                     " && pfIsolationR04().sumChargedHadronPt/pt < 0.2"),
)
process.oneTag  = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("tagMuons"), minNumber = cms.uint32(1))

process.probeMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("patMuonsWithTrigger"),
    cut = cms.string("pt > 10 && numberOfMatchedStations >= 1 && innerTrack.isNonnull"), 
)

process.tpPairs = cms.EDProducer("CandViewShallowCloneCombiner",
    cut = cms.string('60 < mass < 140'),
    decay = cms.string('tagMuons@+ probeMuons@-')
)
process.onePair = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("tpPairs"), minNumber = cms.uint32(1))

process.tpTree = cms.EDAnalyzer("TagProbeFitTreeProducer",
    tagProbePairs = cms.InputTag("tpPairs"),
    arbitration   = cms.string("OneProbe"),
    variables = cms.PSet(
        AllVariables,
        tkValidStripHits = cms.string("track.hitPattern.numberOfValidStripHits"),
        tkLostStripHits = cms.string("track.hitPattern.numberOfLostStripHits('TRACK_HITS')"),
        tkValidStripTIBHits = cms.string("track.hitPattern.numberOfValidStripTIBHits"),
        tkLostStripTIBHits = cms.string("track.hitPattern.numberOfLostStripTIBHits('TRACK_HITS')"),
        tkValidStripTIDHits = cms.string("track.hitPattern.numberOfValidStripTIDHits"),
        tkLostStripTIDHits = cms.string("track.hitPattern.numberOfLostStripTIDHits('TRACK_HITS')"),
        tkValidStripTOBHits = cms.string("track.hitPattern.numberOfValidStripTOBHits"),
        tkLostStripTOBHits = cms.string("track.hitPattern.numberOfLostStripTOBHits('TRACK_HITS')"),
        tkValidStripTECHits = cms.string("track.hitPattern.numberOfValidStripTECHits"),
        tkLostStripTECHits = cms.string("track.hitPattern.numberOfLostStripTECHits('TRACK_HITS')"),
    ),
    flags = cms.PSet(
       TrackQualityFlags,
       MuonIDFlags,
       HighPtTriggerFlags,
       HighPtTriggerFlagsDebug,
    ),
    tagVariables = cms.PSet(
        AllVariables,
        nVertices   = cms.InputTag("nverticesModule"),
        bx     = cms.InputTag("l1rate","bx"),
    ),
    tagFlags = cms.PSet(HighPtTriggerFlags,HighPtTriggerFlagsDebug),
    pairVariables = cms.PSet(
        dz      = cms.string("daughter(0).vz - daughter(1).vz"),
        pt      = cms.string("pt"), 
    ),
    pairFlags = cms.PSet(
    ),
    isMC           = cms.bool(False),
    addRunLumiInfo = cms.bool(True),
)
STEPS = [ 'initialStep', 'lowPtTripletStep', 'pixelPairStep', 'detachedTripletStep', 'mixedTripletStep', 'pixelLessStep', 'tobTecStep', 'jetCoreRegionalStep', 'muonSeededStepInOut', 'muonSeededStepOutIn' ]
for S in STEPS:
    setattr(process.tpTree.flags, 'TK_'+S, cms.string('innerTrack.isAlgoInMask("%s")' % S))
setattr(process.tpTree.flags, 'TK_classic',      cms.string("||".join('innerTrack.isAlgoInMask("%s")' % S for S in STEPS if "muon" not in S and "jetCore" not in S)))
setattr(process.tpTree.flags, 'TK_earlyGeneral', cms.string("||".join('innerTrack.isAlgoInMask("%s")' % S for S in STEPS if "muon" not in S)))
for ID,S,L in (3,'TIB',4), (4,'TID',3), (5,'TOB',6), (6,'TEC',9):
    for iL in xrange(1,L+1):
        setattr(process.tpTree.variables, 'tk%s%dLayerCaseTK' % (S,iL), cms.string("track.hitPattern.getTrackerLayerCase('TRACK_HITS',         %d, %d)" % (ID,iL)))
        setattr(process.tpTree.variables, 'tk%s%dLayerCaseEI' % (S,iL), cms.string("track.hitPattern.getTrackerLayerCase('MISSING_INNER_HITS', %d, %d)" % (ID,iL)))
        setattr(process.tpTree.variables, 'tk%s%dLayerCaseEO' % (S,iL), cms.string("track.hitPattern.getTrackerLayerCase('MISSING_OUTER_HITS', %d, %d)" % (ID,iL)))
        setattr(process.tpTree.flags, 'tk%s%dHitEffNum' % (S,iL), 
                cms.string(          "track.hitPattern.getTrackerLayerCase('TRACK_HITS', %d, %d) == 0" % (ID,iL)))
        setattr(process.tpTree.flags, 'tk%s%dHitEffDen0' % (S,iL), 
                cms.string(          "track.hitPattern.getTrackerLayerCase('TRACK_HITS', %d, %d) <= 1" % (ID,iL)))
        setattr(process.tpTree.flags, 'tk%s%dHitEffDen1' % (S,iL), 
                cms.string("||".join("track.hitPattern.getTrackerLayerCase('%s', %d, %d) <= 1" % (T,ID,iL) for T in 'TRACK_HITS MISSING_INNER_HITS MISSING_OUTER_HITS'.split())))
        setattr(process.tpTree.flags, 'tk%s%dHitEffDen2' % (S,iL), 
                cms.string("||".join("track.hitPattern.getTrackerLayerCase('%s', %d, %d) <= 3" % (T,ID,iL) for T in 'TRACK_HITS MISSING_INNER_HITS MISSING_OUTER_HITS'.split())))
    

process.tagAndProbe = cms.Path( 
    process.triggerResultsFilter +
    process.preselSeq  +
    process.patMuonsWithTriggerSequence +
    process.tagMuons +
    process.oneTag     +
    process.probeMuons +
    process.tpPairs    +
    process.onePair    +
    process.nverticesModule +
    process.l1rate +
    process.tpTree
)

process.TFileService = cms.Service("TFileService", fileName = cms.string("tnpZ_hitEff_Data.root"))

