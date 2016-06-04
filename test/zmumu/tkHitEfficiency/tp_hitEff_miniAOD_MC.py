import FWCore.ParameterSet.Config as cms

process = cms.Process("TagProbe")

process.load('Configuration.StandardSequences.Services_cff')
process.load('FWCore.MessageService.MessageLogger_cfi')
process.options   = cms.untracked.PSet( wantSummary = cms.untracked.bool(True) )
process.MessageLogger.cerr.FwkReport.reportEvery = 100
process.source = cms.Source("PoolSource", 
    fileNames = cms.untracked.vstring('/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0017320C-7BFC-E511-9B2D-0CC47A4C8E34.root')
)

process.maxEvents = cms.untracked.PSet( input = cms.untracked.int32(-1) )    

process.load('Configuration.StandardSequences.GeometryRecoDB_cff')
process.load('Configuration.StandardSequences.MagneticField_38T_cff')
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_condDBv2_cff')
process.load("Configuration.StandardSequences.Reconstruction_cff")

process.GlobalTag.globaltag = cms.string('80X_mcRun2_asymptotic_v4')

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

process.TFileService = cms.Service("TFileService", fileName = cms.string("tnpZ_hitEff_MC.root"))
process.source.fileNames = [
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0017320C-7BFC-E511-9B2D-0CC47A4C8E34.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0061F045-70FC-E511-9BB1-0CC47A4D769A.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0093B392-51FC-E511-9569-5065F381E271.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/00A53F44-7FFC-E511-9435-0CC47A78A4B0.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/00A664C7-DFFC-E511-98E7-0090FAA57330.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/02FEDC0A-7FFC-E511-977D-008CFAF06DDA.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/04430389-61FC-E511-B08E-000F53273730.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/04B0969A-0DFD-E511-A80B-001E67C7AF3F.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/04CEAE8E-D9FC-E511-A7A6-0090FAA1ACF4.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/06D569E4-B5FC-E511-B45F-0090FAA57430.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0812AC71-65FD-E511-BF0F-000F5327373C.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0852310B-B6FD-E511-96B1-0002C94CD0B8.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0A1D15CA-74FC-E511-9919-0CC47A4C8EC6.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0A21CE5A-8BFC-E511-B1F9-782BCB4086A8.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0A3F77E4-DAFC-E511-ACAA-0090FAA58484.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0A4BB8A9-B4FC-E511-BF08-0090FAA57430.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0A4E8103-7BFC-E511-9887-24BE05C63651.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0A944545-52FC-E511-97AC-0002C94D5616.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0AB5B62B-89FC-E511-9C3E-3417EBE64CB1.root',
    '/store/mc/RunIISpring16MiniAODv1/DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8/MINIAODSIM/PUSpring16_80X_mcRun2_asymptotic_2016_v3_ext1-v1/20000/0CAE5668-7FFC-E511-BB82-0025905B858C.root',
]
