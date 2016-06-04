import FWCore.ParameterSet.Config as cms

process = cms.Process("TagProbe")

process.load('Configuration.StandardSequences.Services_cff')
process.load('FWCore.MessageService.MessageLogger_cfi')
process.options   = cms.untracked.PSet( wantSummary = cms.untracked.bool(True) )
process.MessageLogger.cerr.FwkReport.reportEvery = 10
process.MessageLogger.suppressError = cms.untracked.vstring("patTriggerFull")
process.source = cms.Source("PoolSource", 
    fileNames = cms.untracked.vstring('/store/relval/CMSSW_7_4_12/RelValZMM_13/GEN-SIM-RECO/74X_mcRun2_asymptotic_v2-v1/00000/0A812034-4B5C-E511-88E6-003048FFD75C.root'),
)
process.source.fileNames = [
        '/store/relval/CMSSW_7_4_12/RelValZMM_13/GEN-SIM-RECO/PU25ns_74X_mcRun2_asymptotic_v2_v2-v1/00000/22A22515-575E-E511-8AA0-002618943954.root',
        '/store/relval/CMSSW_7_4_12/RelValZMM_13/GEN-SIM-RECO/PU25ns_74X_mcRun2_asymptotic_v2_v2-v1/00000/2EFF2980-515E-E511-BB5B-0025905B8562.root',
        '/store/relval/CMSSW_7_4_12/RelValZMM_13/GEN-SIM-RECO/PU25ns_74X_mcRun2_asymptotic_v2_v2-v1/00000/70809CE0-515E-E511-A508-0025905B8606.root',
        '/store/relval/CMSSW_7_4_12/RelValZMM_13/GEN-SIM-RECO/PU25ns_74X_mcRun2_asymptotic_v2_v2-v1/00000/9EA70DB4-535E-E511-8D78-0025905938AA.root',
        '/store/relval/CMSSW_7_4_12/RelValZMM_13/GEN-SIM-RECO/PU25ns_74X_mcRun2_asymptotic_v2_v2-v1/00000/B2FA120D-4D5E-E511-B140-0025905A608E.root',
        '/store/relval/CMSSW_7_4_12/RelValZMM_13/GEN-SIM-RECO/PU25ns_74X_mcRun2_asymptotic_v2_v2-v1/00000/BC225F0C-575E-E511-B2B4-00261894389D.root',
        '/store/relval/CMSSW_7_4_12/RelValZMM_13/GEN-SIM-RECO/PU25ns_74X_mcRun2_asymptotic_v2_v2-v1/00000/BE3F95F8-4C5E-E511-8437-0025905A610A.root',
        '/store/relval/CMSSW_7_4_12/RelValZMM_13/GEN-SIM-RECO/PU25ns_74X_mcRun2_asymptotic_v2_v2-v1/00000/F2C4E84C-505E-E511-80FF-002618943956.root',
        '/store/relval/CMSSW_7_4_12/RelValZMM_13/GEN-SIM-RECO/PU25ns_74X_mcRun2_asymptotic_v2_v2-v1/00000/F45712F8-4A5E-E511-8428-0025905B85AE.root',
]
process.maxEvents = cms.untracked.PSet( input = cms.untracked.int32(-1) )    

process.load('Configuration.StandardSequences.GeometryRecoDB_cff')
process.load('Configuration.StandardSequences.MagneticField_cff')
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_condDBv2_cff')
process.load("Configuration.StandardSequences.Reconstruction_cff")

from Configuration.AlCa.GlobalTag import GlobalTag
process.GlobalTag = GlobalTag(process.GlobalTag, 'auto:run2_mc', '')

process.load("MuonAnalysis.MuonAssociators.patMuonsWithTrigger_cff")
process.muonMatchHLTL3.maxDeltaR = 0.1
from MuonAnalysis.MuonAssociators.patMuonsWithTrigger_cff import *

from MuonAnalysis.TagAndProbe.common_variables_cff import *
process.load("MuonAnalysis.TagAndProbe.common_modules_cff")

process.tagMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("patMuonsWithTrigger"),
    cut = cms.string("pt > 15 && numberOfMatchedStations >= 2"+
                     " && !triggerObjectMatchesByCollection('hltL3MuonCandidates').empty()"+
                     " && pfIsolationR04().sumChargedHadronPt/pt < 0.2"),
)
process.oneTag  = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("tagMuons"), minNumber = cms.uint32(1))

process.probeMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("patMuonsWithTrigger"),
    cut = cms.string("pt > 10 && numberOfMatchedStations >= 1 && innerTrack.isNonnull"), 
)
process.clusterInfo = cms.EDProducer("ClusterShapeFilterStudies",
        probes = cms.InputTag("probeMuons"),
        estimateCut = cms.double(10), 
        # configuraton for refitter
        DoPredictionsOnly = cms.bool(False),
        Fitter = cms.string('KFFitterForRefitInsideOut'),
        TrackerRecHitBuilder = cms.string('WithAngleAndTemplate'),
        Smoother = cms.string('KFSmootherForRefitInsideOut'),
        MuonRecHitBuilder = cms.string('MuonRecHitBuilder'),
        RefitDirection = cms.string('alongMomentum'),
        RefitRPCHits = cms.bool(True),
        Propagator = cms.string('SmartPropagatorAnyRKOpposite'),
)

process.tpPairs = cms.EDProducer("CandViewShallowCloneCombiner",
    cut = cms.string('60 < mass < 140'),
    decay = cms.string('tagMuons@+ probeMuons@-')
)
process.onePair = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("tpPairs"), minNumber = cms.uint32(1))

from MuonAnalysis.TagAndProbe.muon.tag_probe_muon_extraIso_cff import ExtraIsolationVariables

process.tpTree = cms.EDAnalyzer("TagProbeFitTreeProducer",
    tagProbePairs = cms.InputTag("tpPairs"),
    arbitration   = cms.string("OneProbe"),
    variables = cms.PSet(
        AllVariables,
        clusterChargeM = cms.InputTag("clusterInfo", "median"),
        clusterCharge0 = cms.InputTag("clusterInfo", "byCharge0"),
        clusterCharge1 = cms.InputTag("clusterInfo", "byCharge1"),
        clusterCharge2 = cms.InputTag("clusterInfo", "byCharge2"),
        clusterCharge3 = cms.InputTag("clusterInfo", "byCharge3"),
        clusterCharge4 = cms.InputTag("clusterInfo", "byCharge4"),
        tkValidStripHits = cms.string("? track.isNull ? 0 : track.hitPattern.numberOfValidStripHits"),
        tkLostStripHits = cms.string("? track.isNull ? 0 : track.hitPattern.numberOfLostStripHits('TRACK_HITS')"),
        tkValidStripTIBHits = cms.string("? track.isNull ? 0 : track.hitPattern.numberOfValidStripTIBHits"),
        tkLostStripTIBHits = cms.string("? track.isNull ? 0 : track.hitPattern.numberOfLostStripTIBHits('TRACK_HITS')"),
        tkValidStripTIDHits = cms.string("? track.isNull ? 0 : track.hitPattern.numberOfValidStripTIDHits"),
        tkLostStripTIDHits = cms.string("? track.isNull ? 0 : track.hitPattern.numberOfLostStripTIDHits('TRACK_HITS')"),
        tkValidStripTOBHits = cms.string("? track.isNull ? 0 : track.hitPattern.numberOfValidStripTOBHits"),
        tkLostStripTOBHits = cms.string("? track.isNull ? 0 : track.hitPattern.numberOfLostStripTOBHits('TRACK_HITS')"),
        tkValidStripTECHits = cms.string("? track.isNull ? 0 : track.hitPattern.numberOfValidStripTECHits"),
        tkLostStripTECHits = cms.string("? track.isNull ? 0 : track.hitPattern.numberOfLostStripTECHits('TRACK_HITS')"),
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
        setattr(process.tpTree.variables, 'clusterChargeMin%s%d' % (S,iL), cms.InputTag("clusterInfo","byLayerMin%s%d" %(S,iL)))
        setattr(process.tpTree.variables, 'clusterChargeMax%s%d' % (S,iL), cms.InputTag("clusterInfo","byLayerMax%s%d" %(S,iL)))
    

process.tagAndProbe = cms.Path( 
    process.patMuonsWithTriggerSequence +
    process.tagMuons +
    process.oneTag     +
    process.probeMuons +
    process.tpPairs    +
    process.onePair    +
    process.clusterInfo +
    process.nverticesModule +
    process.l1rate +
    process.tpTree
)

process.TFileService = cms.Service("TFileService", fileName = cms.string("tnpZ_MC.root"))
process.source.fileNames = [
	'/store/relval/CMSSW_8_0_5/RelValZMM_13/GEN-SIM-RECO/PU25ns_80X_mcRun2_asymptotic_v12_gs7120p2-v1/00000/2EEA1A46-D708-E611-ACF6-0025905A6126.root',
	'/store/relval/CMSSW_8_0_5/RelValZMM_13/GEN-SIM-RECO/PU25ns_80X_mcRun2_asymptotic_v12_gs7120p2-v1/00000/6C4B6E3A-D708-E611-B830-0CC47A78A4A6.root',
	'/store/relval/CMSSW_8_0_5/RelValZMM_13/GEN-SIM-RECO/PU25ns_80X_mcRun2_asymptotic_v12_gs7120p2-v1/00000/AA4DB247-D708-E611-A486-0025905A612A.root',
	'/store/relval/CMSSW_8_0_5/RelValZMM_13/GEN-SIM-RECO/PU25ns_80X_mcRun2_asymptotic_v12_gs7120p2-v1/00000/CAFAB841-D708-E611-A028-0CC47A4D7626.root',
	'/store/relval/CMSSW_8_0_5/RelValZMM_13/GEN-SIM-RECO/PU25ns_80X_mcRun2_asymptotic_v12_gs7120p2-v1/00000/F26B2947-D708-E611-8B49-0025905A48F0.root',
	'/store/relval/CMSSW_8_0_5/RelValZMM_13/GEN-SIM-RECO/PU25ns_80X_mcRun2_asymptotic_v12_gs7120p2-v1/00000/F483623F-D708-E611-A6EC-0CC47A4D7662.root',
]
