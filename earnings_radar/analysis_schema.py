"""Structured evidence-grounded analysis; confidence is not a return probability."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Fact(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    evidence_id:int
    field:Literal['title','published_at','url']
    excerpt:str=Field(min_length=1,max_length=2000)

class Analysis(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    event_id:int
    affected_tickers:list[str]
    confirmed_facts:list[Fact]
    hypotheses:list[str]
    economic_mechanism:str
    bullish_implications:list[str]
    bearish_implications:list[str]
    counterevidence:list[str]
    time_horizon:str
    observed_reaction:str
    suggested_action:Literal['investigate','wait','avoid chasing','review exposure','evaluate defined-risk strategy','no attractive trade']
    invalidation_conditions:list[str]
    missing_information:list[str]
    evidence_confidence:Literal['low','medium','high']
    category:Literal['earnings','opportunity','systemic','political','general']
    policy_status:Literal['not_applicable','statement','threat','proposal','reported_signed_action','implementation','amendment','reversal','unknown']
    caveat:str

def validate_analysis(payload,evidence):
    import json
    analysis=Analysis.model_validate(payload)
    if analysis.event_id != evidence['id']:
        raise ValueError('analysis event ID mismatch')
    known=json.loads(evidence['tickers'])
    if set(analysis.affected_tickers)-set(known):
        raise ValueError('unverified company relationship')
    if not analysis.confirmed_facts:
        raise ValueError('at least one evidence reference required')
    for fact in analysis.confirmed_facts:
        if fact.evidence_id != evidence['id'] or fact.excerpt not in evidence[fact.field]:
            raise ValueError('fact does not resolve to stored evidence')
    if analysis.suggested_action=='evaluate defined-risk strategy':
        raise ValueError('analysis cannot suggest a trade without a separate verified evaluation')
    return analysis
