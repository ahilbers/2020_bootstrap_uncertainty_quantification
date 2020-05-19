"""Tests to check whether the models behave as required."""


import os
import logging
import pandas as pd
import models


# Install costs and generation costs. These should match the information
# provided in the model.yaml and techs.yaml files in the model definition
COSTS = pd.DataFrame(columns=['install', 'generation'])

# Costs for 1 region model
COSTS.loc['baseload'] = [300., 0.005]
COSTS.loc['peaking']  = [100., 0.035]
COSTS.loc['wind']     = [100., 0.000]
COSTS.loc['unmet']    = [  0., 6.000]

# Heterogenised costs for 6 region model
COSTS.loc['ccgt_region1']    = [100.1, 0.035001]
COSTS.loc['ocgt_region1']    = [ 50.1, 0.100001]
COSTS.loc['wind_region2']    = [ 90.2, 0.000002]
COSTS.loc['nuclear_region3'] = [300.3, 0.005003]
COSTS.loc['ccgt_region3']    = [100.3, 0.035003]
COSTS.loc['wind_region5']    = [100.5, 0.000005]
COSTS.loc['ocgt_region6']    = [ 50.6, 0.100006]
COSTS.loc['wind_region6']    = [ 70.6, 0.000006]
COSTS.loc['unmet_region2']   = [    0, 6.000002]
COSTS.loc['unmet_region4']   = [    0, 6.000004]
COSTS.loc['unmet_region5']   = [    0, 6.000005]
COSTS.loc['transmission_region1_region2'] = [100.12, 0]
COSTS.loc['transmission_region1_region5'] = [150.15, 0]
COSTS.loc['transmission_region1_region6'] = [130.16, 0]
COSTS.loc['transmission_region2_region3'] = [100.23, 0]
COSTS.loc['transmission_region3_region4'] = [100.34, 0]
COSTS.loc['transmission_region4_region5'] = [100.45, 0]
COSTS.loc['transmission_region5_region6'] = [100.56, 0]


# Topology of 6 region model. These should match the information provided
# in the locations.yaml files in the model definition
NUCLEAR_TOP, CCGT_TOP, OCGT_TOP, WIND_TOP, UNMET_TOP, DEMAND_TOP = (
    [('nuclear', i) for i in ['region3']],
    [('ccgt', i) for i in ['region1', 'region3']],
    [('ocgt', i) for i in ['region1', 'region6']],
    [('wind', i) for i in ['region2', 'region5', 'region6']],
    [('unmet', i) for i in ['region2', 'region4', 'region5']],
    [('demand', i) for i in ['region2', 'region4', 'region5']]
)
TRANSMISSION_TOP = [('transmission', *i)
                    for i in [('region1', 'region2'),
                              ('region1', 'region5'),
                              ('region1', 'region6'),
                              ('region2', 'region3'),
                              ('region3', 'region4'),
                              ('region4', 'region5'),
                              ('region5', 'region6')]]


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

    out = model.get_summary_outputs()
    res = model.results
    corrfac = 8760/model.num_timesteps    # For annualisation

    # Test if generation technology installation costs are consistent
    if run_mode == 'plan':
        for tech, region in NUCLEAR_TOP + CCGT_TOP + OCGT_TOP + WIND_TOP:
            cost_method1 = float(
                COSTS.loc['{}_{}'.format(tech, region), 'install'] *
                out.loc['cap_{}_{}'.format(tech, region)]
            )
            cost_method2 = corrfac * float(
                res.cost_investment[0].loc['{}::{}_{}'.format(region,
                                                              tech,
                                                              region)]
            )
            if abs(cost_method1 - cost_method2) > 0.1:
                logging.error('FAIL: %s install costs in %s do not match!\n'
                              '    manual: %s, model: %s',
                              tech, region, cost_method1, cost_method2)
                passing = False
            cost_total_method1 += cost_method1

    # Test if transmission installation costs are consistent
    if run_mode == 'plan':
        for tech, region_a, region_b in TRANSMISSION_TOP:
            cost_method1 = float(
                COSTS.loc[
                    '{}_{}_{}'.format(tech, region_a, region_b), 'install'
                ] * out.loc[
                    'cap_transmission_{}_{}'.format(region_a, region_b)
                ]
            )
            cost_method2 = 2 * corrfac * \
                float(res.cost_investment[0].loc[
                    '{}::{}_{}_{}:{}'.format(region_a,
                                             tech,
                                             region_a,
                                             region_b,
                                             region_b)
                ])
            if abs(cost_method1 - cost_method2) > 0.1:
                logging.error('FAIL: %s install costs from %s to %s do '
                              'not match!\n    manual: %s, model: %s',
                              tech, region_a, region_b,
                              cost_method1, cost_method2)
                passing = False
            cost_total_method1 += cost_method1

    # Test if generation costs are consistent
    for tech, region in NUCLEAR_TOP + CCGT_TOP + OCGT_TOP + WIND_TOP + UNMET_TOP:
        cost_method1 = float(
            COSTS.loc['{}_{}'.format(tech, region), 'generation']
            * out.loc['gen_{}_{}'.format(tech, region)]
        )
        cost_method2 = corrfac * float(
            res.cost_var[0].loc['{}::{}_{}'.format(region, tech, region)].sum()
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
    generation_total = float(out.loc[['gen_nuclear_total',
                                      'gen_ccgt_total',
                                      'gen_ocgt_total',
                                      'gen_wind_total',
                                      'gen_unmet_total']].sum())
    demand_total = float(out.loc['demand_total'])
    if abs(generation_total - demand_total) > 0.1:
        logging.error('FAIL: generation does not match demand!\n'
                      '    generation: %s, demand: %s',
                      generation_total, demand_total)
        passing = False

    return passing


def test_outputs_against_benchmark(model_name, run_mode,
                                   baseload_integer, baseload_ramping,
                                   allow_unmet):
    """Test model outputs against benchmark."""

    # Load time series data
    ts_data = models.load_time_series_data(model_name=model_name)
    ts_data = ts_data.loc['2017-01']    # Should match benchmarks

    # Run a simulation on which to run tests
    logging.info('TESTS: Running test simulation...')
    if model_name == '1_region':
        Model = models.OneRegionModel
    elif model_name == '6_region':
        Model = models.SixRegionModel
    else:
        raise ValueError('Valid model names: 1_region, 6_region')
    model = Model(ts_data=ts_data, run_mode=run_mode,
                  baseload_integer=baseload_integer,
                  baseload_ramping=baseload_ramping,
                  allow_unmet=allow_unmet, extra_override=None)
    model.run()
    logging.info('TESTS: Done running test simulation \n')
    summary_outputs = model.get_summary_outputs()

    # Test internal consistency of outputs -- do costs add up?
    if model_name == '1_region':
        passing_consistent = test_output_consistency_1_region(model,
                                                              run_mode)
    elif model_name == '6_region':
        passing_consistent = test_output_consistency_6_region(model,
                                                              run_mode)

    # Load benchmarks
    if not baseload_integer and not baseload_ramping:
        baseload_name = 'continuous'
    elif baseload_integer and baseload_ramping:
        baseload_name = 'integer_ramping'
    unmet_name = 'unmet' if allow_unmet else 'nounmet'
    benchmark_outputs = pd.read_csv(
        os.path.join('benchmarks', '{}_{}_{}_{}_2017-01.csv'.format(
            model_name, run_mode, baseload_name, unmet_name)), index_col=0
    )

    # Test outputs against benchmark
    passing_benchmarks = True
    rel_error = abs((summary_outputs - benchmark_outputs) / benchmark_outputs)
    if float(rel_error.max()) > 1e-6:
        logging.error('FAIL: Model outputs do not match benchmark outputs!\n'
                      'Model outputs: \n%s\n \nBenchmark outputs:\n%s\n',
                      summary_outputs, benchmark_outputs)
        passing_benchmarks = False

    if passing_consistent:
        print('PASS: model outputs are consistent.')  # To stdout
    if passing_benchmarks:
        print('PASS: model outputs match benchmarks.')   # To stdout

    return passing_consistent, passing_benchmarks


def run_all_benchmarks():
    passing_consistent_list = []
    passing_benchmarks_list = []
    runs = [('1_region', 'plan', False, False, False),
            ('1_region', 'plan', False, False, True),
            ('1_region', 'plan', True, True, False),
            ('1_region', 'plan', True, True, True),
            ('1_region', 'operate', False, False, True),
            ('1_region', 'operate', True, True, True),
            ('6_region', 'plan', False, False, False),
            ('6_region', 'plan', False, False, True),
            ('6_region', 'plan', True, True, False),
            ('6_region', 'plan', True, True, True),
            ('6_region', 'operate', False, False, True),
            ('6_region', 'operate', True, True, True)]
    for model_name, run_mode, baseload_integer, baseload_ramping, allow_unmet in runs:
        print('{}, {}, baseload_integer: {}, baseload_ramping: {}, '
              'allow_unmet: {}'.format(model_name, run_mode, baseload_integer,
                                       baseload_ramping, allow_unmet))
        print('----------------------------------------------------------')
        passing_consistent, passing_benchmarks = (
            test_outputs_against_benchmark(model_name=model_name,
                                           run_mode=run_mode,
                                           baseload_integer=baseload_integer,
                                           baseload_ramping=baseload_ramping,
                                           allow_unmet=allow_unmet)
        )
        passing_consistent_list.append(passing_consistent)
        passing_benchmarks_list.append(passing_benchmarks)
        print('\n\n')

    # Display summaries -- to stdout (no logging here)
    if all(passing_consistent_list):
        print('PASS: all model outputs are consistent.')
    else:
        print('FAIL: some model outputs are not consistent.')
    if all(passing_benchmarks_list):
        print('PASS: all model outputs match benchmarks.')
    else:
        print('FAIL: some benchmarks have failed.')


if __name__ == '__main__':
    run_all_benchmarks()
