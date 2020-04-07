"""Tests to check whether the models behave as required."""


import os
import logging
import pandas as pd
import models


# Install costs and generation costs. These should match the information
# provided in the model.yaml and techs.yaml files in the model definition
COSTS = pd.DataFrame(columns=['install', 'generation'])
COSTS.loc['baseload']                = [300., 0.005]
COSTS.loc['peaking']                 = [100., 0.035]
COSTS.loc['wind']                    = [100., 0.   ]
COSTS.loc['unmet']                   = [  0., 6.   ]
COSTS.loc['transmission_other']      = [100., 0.   ]
COSTS.loc['transmission_region1to5'] = [150., 0.   ]


# Topology of 6 region model. These should match the information provided
# in the locations.yaml files in the model definition
BASELOAD_TOP, PEAKING_TOP, WIND_TOP, UNMET_TOP, DEMAND_TOP = (
    [('baseload', i) for i in ['region1', 'region3', 'region6']],
    [('peaking', i) for i in ['region1', 'region3', 'region6']],
    [('wind', i) for i in ['region2', 'region5', 'region6']],
    [('unmet', i) for i in ['region2', 'region4', 'region5']],
    [('demand', i) for i in ['region2', 'region4', 'region5']]
)
TRANSMISSION_REGION1TO5_TOP, TRANSMISSION_OTHER_TOP = (
    [('transmission_region1to5', 'region1', 'region5')],
    [('transmission_other', *i) for i in [('region1', 'region2'),
                                          ('region1', 'region6'),
                                          ('region2', 'region3'),
                                          ('region3', 'region4'),
                                          ('region4', 'region5'),
                                          ('region5', 'region6')]]
)


def test_output_consistency_1_region(model, run_mode):
    """Check if model outputs are internally consistent for 6 region model.

    Parameters:
    -----------
    model (calliope.Model) : instance of OneRegionModel or SixRegionModel
    run_mode (str) : 'plan' or 'operate'

    Returns:
    --------
    passing: True if test is passed, False otherwise
    """

    passing = True
    cost_total_method1 = 0

    out = model.get_summary_outputs()
    res = model.results
    corrfac = 8760/model.num_timesteps    # For annualisation

    # Test if generation technology installation costs are consistent
    if run_mode == 'plan':
        for tech in ['baseload', 'peaking', 'wind']:
            cost_method1 = float(COSTS.loc[tech, 'install']
                                 * out.loc['cap_{}_total'.format(tech)])
            cost_method2 = corrfac * float(
                res.cost_investment[0].loc['region1::{}'.format(tech)]
            )
            if abs(cost_method1 - cost_method2) > 0.1:
                logging.error('FAIL: %s install costs do not match!\n'
                              '    manual: %s, model: %s',
                              tech, cost_method1, cost_method2)
                passing = False
            cost_total_method1 += cost_method1

    # Test if generation costs are consistent
    for tech in ['baseload', 'peaking', 'wind', 'unmet']:
        cost_method1 = float(COSTS.loc[tech, 'generation']
                             * out.loc['gen_{}_total'.format(tech)])
        cost_method2 = corrfac * float(res.cost_var[0].loc[
            'region1::{}'.format(tech)
        ].sum())
        if abs(cost_method1 - cost_method2) > 0.1:
            logging.error('FAIL: %s generation costs do not match!\n'
                          '    manual: %s, model: %s',
                          tech, cost_method1, cost_method2)
            passing = False
        cost_total_method1 += cost_method1

    # Test if total costs are consistent
    if run_mode == 'plan':
        cost_total_method2 = corrfac * float(res.cost.sum())
        if abs(cost_total_method1 - cost_total_method2) > 0.1:
            logging.error('FAIL: total system costs do not match!\n'
                          '    manual: %s, model: %s',
                          cost_total_method1, cost_total_method2)
            passing = False

    # Test if supply matches demand
    generation_total = float(out.loc[['gen_baseload_total',
                                      'gen_peaking_total',
                                      'gen_wind_total',
                                      'gen_unmet_total']].sum())
    demand_total = float(out.loc['demand_total'])
    if abs(generation_total - demand_total) > 0.1:
        logging.error('FAIL: generation does not match demand!\n'
                      '    generation: {}, demand: {}'.format(generation_total,
                                                              demand_total))
        passing = False

    return passing


def test_output_consistency_6_region(model, run_mode):
    """Check if model outputs are internally consistent for 6 region model.

    Parameters:
    -----------
    model (calliope.Model) : instance of OneRegionModel or SixRegionModel
    run_mode (str) : 'plan' or 'operate'

    Returns:
    --------
    passing: True if test is passed, False otherwise
    """

    passing = True
    cost_total_method1 = 0

    out = model.get_summary_outputs(at_regional_level=True)
    res = model.results
    corrfac = 8760/model.num_timesteps    # For annualisation

    # Test if generation technology installation costs are consistent
    if run_mode == 'plan':
        for tech, region in BASELOAD_TOP + PEAKING_TOP + WIND_TOP:
            cost_method1 = float(
                COSTS.loc[tech, 'install'] *
                out.loc['cap_{}_{}'.format(tech, region)]
            )
            cost_method2 = corrfac * float(
                res.cost_investment[0].loc['{}::{}'.format(region, tech)]
            )
            if abs(cost_method1 - cost_method2) > 0.1:
                logging.error('FAIL: %s install costs in %s do not match!\n'
                              '    manual: %s, model: %s',
                              tech, region, cost_method1, cost_method2)
                passing = False
            cost_total_method1 += cost_method1

    # Test if transmission installation costs are consistent
    if run_mode == 'plan':
        for tech, region_a, region_b in \
            TRANSMISSION_REGION1TO5_TOP + TRANSMISSION_OTHER_TOP:
            cost_method1 = float(
                COSTS.loc[tech, 'install'] * out.loc[
                    'cap_transmission_{}_{}'.format(region_a, region_b)
                ]
            )
            cost_method2 = 2 * corrfac * \
                float(res.cost_investment[0].loc[
                    '{}::{}:{}'.format(region_a, tech, region_b)
                ])
            if abs(cost_method1 - cost_method2) > 0.1:
                logging.error('FAIL: %s install costs from %s to %s do '
                              'not match!\n    manual: %s, model: %s',
                              tech, region_a, region_b,
                              cost_method1, cost_method2)
                passing = False
            cost_total_method1 += cost_method1

    # Test if generation costs are consistent
    for tech, region in BASELOAD_TOP + PEAKING_TOP + WIND_TOP + UNMET_TOP:
        cost_method1 = float(
            COSTS.loc[tech, 'generation']
            * out.loc['gen_{}_{}'.format(tech, region)]
        )
        cost_method2 = corrfac * float(
            res.cost_var[0].loc[region + '::' + tech].sum()
        )
        if abs(cost_method1 - cost_method2) > 0.1:
            logging.error('FAIL: %s generation costs in %s do not match!\n'
                          '    manual: %s, model: %s', 
                          tech, region, cost_method1, cost_method2)
            passing = False
        cost_total_method1 += cost_method1

    # Test if total costs are consistent
    if run_mode == 'plan':
        cost_total_method2 = corrfac * float(res.cost.sum())
        if abs(cost_total_method1 - cost_total_method2) > 0.1:
            logging.error('FAIL: total system costs do not match!\n'
                          '    manual: %s, model: %s',
                          cost_total_method1, cost_total_method2)
            passing = False

    # Test if supply matches demand
    generation_total = float(out.loc[['gen_baseload_total',
                                      'gen_peaking_total',
                                      'gen_wind_total',
                                      'gen_unmet_total']].sum())
    demand_total = float(out.loc['demand_total'])
    if abs(generation_total - demand_total) > 0.1:
        logging.error('FAIL: generation does not match demand!\n'
                      '    generation: %s, demand: %s',
                      generation_total, demand_total)
        passing = False

    return passing
