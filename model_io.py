"""Structured model import. Files are data only and are never executed."""
import copy
import json
import math
from datetime import date
from engine import load_data, latest_key, validate_case, evaluate, audit, monte_carlo

def validate_model(candidate):
    """Reject malformed or unreconciled imports before activation."""
    reference = load_data()
    if not isinstance(candidate, dict):
        raise ValueError('The import must be a JSON object.')
    def same_structure(value, template, path):
        if isinstance(template, dict):
            if not isinstance(value, dict):
                raise ValueError(path + ' must be an object.')
            for key, example in template.items():
                if key not in value:
                    raise ValueError(path + '.' + key + ' is missing.')
                same_structure(value[key], example, path + '.' + key)
        elif isinstance(template, bool):
            if not isinstance(value, bool):
                raise ValueError(path + ' must be true or false.')
        elif isinstance(template, (float, int)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(path + ' must be a finite number.')
        elif isinstance(template, str):
            if not isinstance(value, str):
                raise ValueError(path + ' must be text.')
        elif isinstance(template, list):
            if not isinstance(value, list):
                raise ValueError(path + ' must be a list.')
    same_structure(candidate, reference, 'model')
    if candidate['company'] != reference['company'] or candidate['ticker'] != reference['ticker']:
        raise ValueError('This template is for PT Darma Henwa Tbk (IDX:DEWA).')
    if candidate['unit'] != reference['unit']:
        raise ValueError('Keep model units in IDR billion and shares in millions.')
    for key in ['prepared', 'valuation_date', 'financial_date']:
        date.fromisoformat(candidate[key])
    if date.fromisoformat(candidate['financial_date']) > date.fromisoformat(candidate['valuation_date']):
        raise ValueError('Financial date must not follow the valuation date.')
    months = candidate.get('latest_period_months', 9)
    if type(months) is not int or months not in (3,6,9,12):
        raise ValueError('Latest period months must be 3, 6, 9 or 12 (cumulative calendar-year statements).')
    if date.fromisoformat(candidate['financial_date']).month != months:
        raise ValueError('Financial date month must match cumulative latest period months.')
    key = latest_key(candidate)
    if key not in candidate['historical']:
        raise ValueError('Latest period is absent from historical data.')
    same_structure(candidate['historical'][key], reference['historical']['Q3YTD2026'], 'latest historical period')
    tax_period = candidate.get('exploration_tax_period', 'FY2025')
    if tax_period not in candidate['historical'] or 'exploration_dtl' not in candidate['historical'][tax_period]:
        raise ValueError('Exploration tax period requires an exploration_dtl input.')
    for period, values in candidate['historical'].items():
        for field, value in values.items():
            if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value):
                raise ValueError(f'{period}.{field} must be a finite number in IDR billion.')
    if not 0 < candidate['market']['shares_m'] or not 0 < candidate['market']['price']:
        raise ValueError('Price and share count must be positive.')
    if not candidate['market']['price_source'] or not candidate['market']['shares_source']:
        raise ValueError('Market sources must be provided.')
    for field in ['tax','noncash_lease_capex_ratio','core_source_quality','forecast_visibility','peer_quality','asset_observability']:
        if not 0 <= candidate['assumptions'][field] <= 1:
            raise ValueError(field + ' must be between 0 and 1.')
    if set(candidate['scenarios']) != {'Bear','Base','Bull'}:
        raise ValueError('Keep Bear, Base and Bull scenarios.')
    for name, case in candidate['scenarios'].items():
        same_structure(case, reference['scenarios'][name], name)
        validate_case(case)
        if not 0 <= case['probability'] <= 1:
            raise ValueError('Scenario probabilities must be between 0 and 1.')
    if not candidate['peers']:
        raise ValueError('Keep the peer register, even when all peers are excluded.')
    for peer in candidate['peers']:
        same_structure(peer, reference['peers'][0], 'peer')
    if not candidate['records']:
        raise ValueError('An input source register is required.')
    for record in candidate['records']:
        same_structure(record, reference['records'][0], 'source record')
    for name in candidate['scenarios']:
        result = evaluate(candidate, name)
        if result['dcf']['ev'] <= 0:
            raise ValueError('Operating EV must be positive for this going-concern template.')
    checks = audit(candidate)
    failed = [c['check'] for c in checks if c['status'] != 'PASS']
    if failed:
        raise ValueError('Reconcile these checks before importing: ' + ', '.join(failed[:8]))
    # Also check the fixed simulation ranges against the imported Base case.
    monte_carlo(candidate)
    return copy.deepcopy(candidate)

def parse_model(raw):
    if len(raw) > 2_000_000:
        raise ValueError('Model JSON must be smaller than 2 MB.')
    try:
        candidate = json.loads(raw)
        return validate_model(candidate)
    except (KeyError, TypeError, AttributeError, ZeroDivisionError, OverflowError) as error:
        raise ValueError('Incomplete or incompatible model template: ' + str(error)) from error
