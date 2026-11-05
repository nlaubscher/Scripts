##!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

# ─────────────────────────────
# Standard library imports
# ─────────────────────────────
import logging
import os
import sys
from collections import OrderedDict

# Path modification (keep directly after sys import)
sys.path.append(r'C:\work\SVN\SensiLab\chemical\sequences\chimaera\run_gms')

# ─────────────────────────────
# Third-party imports
# ─────────────────────────────
import numpy as np

# ─────────────────────────────
# Sensirion / project-specific imports
# ─────────────────────────────
from pilatus import conversion

from sensirion_sensilab_core import ConcentrationSignal, SensiLabSetup
from sensirion_sensilab_core.devices.platforms.dummy_platform import DummyPlatform
from sensirion_sensilab_espec.labdevice.espec_p310_ethernet import ESPECEthernet
# from sensirion_sensilab_gms.lab_devices.gms import GMS
from sensirion_sensilab_gms.lab_devices.pressure_gms import PressureGMS
from sensirion_sensilab_gms.lab_devices.controllers.pressure_controller import (
    PressureController,
)
# from sensirion_sensilab_yoctopuce_driver.converter import CurrentLoopConverter
# from sensirion_sensilab_yoctopuce_driver.yocto_rx import YoctoRx
from sensirion_sensilab_edinburgh_gascard.gascard import GascardDevice

from sensirion_sensilab_chimaera_carasso_internal.platforms.pilatus_chimaera_carasso_c4_latest import (
    PilatusTcProfilesCarassoC4, PilatusContinuousCarassoC4)
from sensirion_sensilab_chimaera_carasso_internal.platforms.pilatus_carasso_c4_helper_functions import (
    pilatus_tc_profile_measure_every_during, recalib_tsens)

import json

logger = logging.getLogger(__name__)
# OTP version of the macro
NR_OF_CHANNELS = 32

#*********** User Input **********

OPERATOR = 'NLAU'
MMNT_NR =  'test' #'CHI031_02' #'CHI028_01' #
MEASUREMENT_SESSION = f"{MMNT_NR}_C4_annealing_Tsens_recalib"


PILATUS_IPS = [
    # '192.168.100.100',
    # '192.168.100.101',
    '192.168.100.168'
]

SIMULATE = False# True
SAMPLING_RATE = 4 # every x seconds
PRE_MMMT_TIME = 20. # min               ?????????????????

V_HEATER_ANNEAL = 5 # V
V_HEATER_RECALIB = 4 # V

ACTIVE_MASK = 32 * [True]

nan = float('nan')
no_heat_list = [nan, nan, nan, nan]

path_power_calib = None

T_OFF = nan
T_ANNEALING = 700.,

# All pixels active
L_ALL_PX = [
    [T_ANNEALING]*32,  # Px1
    [T_ANNEALING]*32,  # Px2
    [T_ANNEALING]*32,  # Px3
    [T_ANNEALING]*32,  # Px4
]

# Annealing schedule
TIME_TEMP_LIST = [
    (10,  L_ALL_PX),      # 10 min
    (10,  L_ALL_PX),      # 20 min total
    (10,  L_ALL_PX),      # 30 min total
    (10,  L_ALL_PX),      # 40 min total
    (10,  L_ALL_PX),      # 50 min total
    (10,  L_ALL_PX),      # 60 min total
]

BACKDOOR = True

STD_AH = 7.5 # g/m3
STD_FLOW = 1.0  # l/min
STD_PRESSURE = 1e5  # Pa
STD_TEMPERATURE = 20. # degC

# Pulse mask: Important: Use only values 0 (always burn) or 65535 (never burn)
#   or exponentials of 2, e.g. PULSE_MASK either 0, 1, 2, 4, 8, 16, ..., 32768. In that case the period (on and off
#   combined) is given by T_period = 1.31 * PULSE_MASK seconds.
#   For further options see Sensinet folder "Chimaera\03_RD\01_RDC\02_PythonScripts\pulse_mask_simulator.ipynb"

# Heater-controller settings (see Carasso NPD)
HEAT_CTRL_CFG = {
    'ChopFrq': 1,  # 0: 0, 1: f_adc / 256, 2: f_adc / 4, 3: f_adc / 2, Default: 1
    'FAdc': 0,  # 0: 800 kHz, 1: 400 kHz
    'NsShpFrq': 0,  # 0: 800 kHz, 1: 1600 kHz
    'N': 3  # 0: 2, 1: 4, 2: 8, 3: 16, 4: 32, 5: 64, 6: 128, 7: 256
}


with SensiLabSetup(config_project=r'C:\work\SVN\SensiLab\chemical\configs\project\chemical_chimaera_config_project.ini',
                   logging_level=logging.INFO,
                   metadata=dict(Operator=OPERATOR), simulate=SIMULATE) as setup:
    gms = setup.lab_devices['GMS']
    assert isinstance(gms, PressureGMS)

    pressure_controller = setup.lab_devices['PressureController']
    assert isinstance(pressure_controller, PressureController)

    espec = setup.lab_devices['Oven']
    assert isinstance(espec, ESPECEthernet)

    setup.start_measurement_session(MEASUREMENT_SESSION)
    setup.wait(1)

    pressure_controller.set_pressure(STD_PRESSURE, wait_until_stable=False)
    espec.start()
    setup.wait(1)
    espec.set_temperature(STD_TEMPERATURE)

    setup.wait(1)

    pilati = []

    for _ip in PILATUS_IPS:
        pilati.append(PilatusContinuousCarassoC4(
            setup,
            ip_address=_ip,
            backdoor=BACKDOOR,
            active_mask=ACTIVE_MASK,
            voltage_heater=V_HEATER_ANNEAL, # 5V
            path_power_calib=path_power_calib,
        ))

    
    setup.start_measurement_series(f'PreMmnt_RTsens_NoHeat')
    for pilatus in pilati:
        pilatus.start_continuous_measurement(t_set_degc=no_heat_list)
    gms.set_gas_mix(dict(Propane=0 * 1e-6, CO2=0 * 1e-6, AH=STD_AH), flow=STD_FLOW, ignore_min_flow=True,
                    ignore_humidity_range=True)
    setup.measure_every_during(every_sec=SAMPLING_RATE, during_min=PRE_MMMT_TIME)

    for pilatus in pilati:
        pilatus.stop_measurement()
        setup.wait(1)


    #Platform change because of Voltage_Heater change for recalib
    for pilatus in pilati:
        pilatus.self_destroy()
    pilati = []
    for _ip in PILATUS_IPS:
        pilati.append(PilatusContinuousCarassoC4(
            setup,
            ip_address=_ip,
            backdoor=BACKDOOR,
            active_mask=ACTIVE_MASK,
            voltage_heater=V_HEATER_RECALIB,
            path_power_calib=path_power_calib,
        ))

    # Perform power-based T-sensor recalibration (all pixels)
    setup.start_measurement_series(f'TSensorRecalib_PreAnnealing')
    path_power_calib = recalib_tsens(setup=setup, pilatus_handles=pilati)

    #Platform change because of Voltage_Heater change
    for pilatus in pilati:
        pilatus.self_destroy()
    pilati = []
    for _ip in PILATUS_IPS:
        pilati.append(PilatusContinuousCarassoC4(
            setup,
            ip_address=_ip,
            backdoor=BACKDOOR,
            active_mask=ACTIVE_MASK,
            voltage_heater=V_HEATER_ANNEAL,
            path_power_calib=path_power_calib,
        ))

    # Annealing with recalib as defined in TIME_TEMP_LIST
    for step_nr, (duration, T_list) in enumerate(TIME_TEMP_LIST):
        # Perform this annealing segment at the current step temperature.
        setup.start_measurement_series(f'AnnealingStep_{step_nr}')
        for pilatus in pilati:
            pilatus.start_continuous_measurement(t_set_degc=T_list)

        gms.set_gas_mix(dict(Propane=0 * 1e-6, CO2=0 * 1e-6, AH=STD_AH), flow=STD_FLOW, ignore_min_flow=True,
                        ignore_humidity_range=True)
        setup.measure_every_during(every_sec=SAMPLING_RATE, during_min=duration)

        for pilatus in pilati:
            pilatus.stop_measurement()
            setup.wait(1)

        #change platform with new voltage and perform recalib
        for pilatus in pilati:
            pilatus.self_destroy()
        pilati = []
        for _ip in PILATUS_IPS:
            pilati.append(PilatusContinuousCarassoC4(
                setup,
                ip_address=_ip,
                backdoor=BACKDOOR,
                active_mask=ACTIVE_MASK,
                voltage_heater=V_HEATER_RECALIB,
                path_power_calib=path_power_calib,
            ))

        setup.start_measurement_series(f'TSensorRecalib_{step_nr}')
        path_power_calib = recalib_tsens(setup=setup, pilatus_handles=pilati)

        for pilatus in pilati:
            pilatus.self_destroy()
        pilati = []
        for _ip in PILATUS_IPS:
            pilati.append(PilatusContinuousCarassoC4(
                setup,
                ip_address=_ip,
                backdoor=BACKDOOR,
                active_mask=ACTIVE_MASK,
                voltage_heater=V_HEATER_ANNEAL,
                path_power_calib=path_power_calib,
            ))


    #Platform change because of Voltage_Heater change
    for pilatus in pilati:
        pilatus.self_destroy()
    pilati = []
    for _ip in PILATUS_IPS:
        pilati.append(PilatusContinuousCarassoC4(
            setup,
            ip_address=_ip,
            backdoor=BACKDOOR,
            active_mask=ACTIVE_MASK,
            voltage_heater=V_HEATER_ANNEAL,
            path_power_calib=path_power_calib,
        ))
    # post measutement 
    setup.start_measurement_series(f'PostMmnt_RTsens_NoHeat')

    for pilatus in pilati:
        pilatus.start_continuous_measurement(
            t_set_degc=no_heat_list
        )

    gms.set_gas_mix(dict(Propane=0 * 1e-6, CO2=0 * 1e-6, AH=STD_AH), flow=STD_FLOW, ignore_min_flow=True,
                    ignore_humidity_range=True)
    setup.measure_every_during(every_sec=SAMPLING_RATE, during_min=5)

    for pilatus in pilati:
        pilatus.stop_measurement()
        setup.wait(1)

    espec.stop()