##!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

# ─────────────────────────────
# Standard library imports
# ─────────────────────────────
import logging
import math
import sys

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

# ─────────────────────────────
# Carasso specific imports
# ─────────────────────────────
from sensirion_sensilab_chimaera_carasso_internal.platforms.pilatus_carasso_c4_tc_profile import (
    PilatusTcProfilesCarassoC4_1b00)
from sensirion_sensilab_chimaera_carasso_internal.platforms.pilatus_tc_profile_measurement import (
    pilatus_tc_profile_measure_every_during)



logger = logging.getLogger(__name__)

# *********** User input **************

OPERATOR = 'JUB'
MMNT_NR = 'test' # 'CHI031_07' # '
MEASUREMENT_SESSION = f"{MMNT_NR}_C4_profile_steps"

SIMULATE = False # True
MEASURE_SENSORS = not SIMULATE

SENSOR_TYPE = "C4"
VOLTAGE_HEATER = 4
CONTINUOUS = False

T_AH_dict = {
    # 5: (5, [0, 5]),#T : (STD_AH_of_T, AH_steps) g/m3
    20: (11.5, [0, 11.5]), # 20°C-> max 14 g/m3 at 10000 Pa
    50: (11.5, [7.5, 11.5, 35, 50]),
    80: (11.5, [7.5, 11.5, 35, 50])
    }

# Pilatus IP adresses, including the pathes of the power calibration
TSENS_CALIB_PATH = r'L:\Chemical\MmntSetups\Chimaera\2026_09\20260929T141743Z_CHI031_10_C4_Tsens_recalib_8059\20260929T142857Z_TSensorRecalib_B787\bridge_data_files'
IP_ADDRESSES = {
    '192.168.100.102': {
        'PathPowerCalib': TSENS_CALIB_PATH
    },
   '192.168.100.100': {
       'PathPowerCalib': TSENS_CALIB_PATH
    },
    '192.168.100.101': {
        'PathPowerCalib': TSENS_CALIB_PATH
    },
    '192.168.100.168': {
        'PathPowerCalib': TSENS_CALIB_PATH
    },
}

# Carasso specific input
BACKDOOR = True
ACTIVE_MASK = 32 * [True]
OTP_VERSION = 2

# Profile: List of maximal 10 entries, corresponding to the up to 10 profile steps.
#   Each entry must be a list of the 4 pixels in degrees Celsius.
#   Use float('nan') for no heating.
nan = float('nan')
PROFILE_TEMPS = [
    nan,
    80.,
    140.,
    200.,
    260.,
    320.,
    380.,
    440.,
    500.,
    560.,
]

HEATED_BRIDGES = {
    "C2": [0, 2],  # Px1, Px3
    "C4": [1, 3],  # Px2, Px4
}

def build_profile(profile_temps, sensor_type):
    heated_bridges = HEATED_BRIDGES[sensor_type]

    profile = []
    for temp in profile_temps:
        step = [nan] * 4

        # works for both normal values and NaN
        for bridge in heated_bridges:
            step[bridge] = temp

        profile.append(step)

    return profile


PROFILE = build_profile(
    profile_temps=PROFILE_TEMPS,
    sensor_type=SENSOR_TYPE,
)


# Time to wait in milliseconds for each profile step
STEP_WAIT_TIME_MS = 100.

# Averaging of Noise-shaper input, Decimator output and TJunction. Choose 32, 64 or 128
N_AVG = 128

# Heater controller config
HEAT_CTRL_CFG = {
    'ChopFrq': 1,  # 0: 0, 1: f_adc / 256, 2: f_adc / 4, 3: f_adc / 2, Default: 1
    'FAdc': 0,  # 0: 800 kHz, 1: 400 kHz
    'NsShpFrq': 0,  # 0: 800 kHz, 1: 1600 kHz
    'N': 3  # 0: 2, 1: 4, 2: 8, 3: 16, 4: 32, 5: 64, 6: 128, 7: 256
}

# Sampling rate must be large enough for sensors to finish
SAMPLING_RATE = 0.2 + len(PROFILE) * (0.015 + N_AVG * 0.00256 + 0.001 * STEP_WAIT_TIME_MS)

# Time to wait for Tjunction measurement
WAIT_TIME_TJ_SEC = 1e-3 * N_AVG * 4 # Important for remote T-sensor option.

# to be discussed
LOG_INTERVAL = 4
STD_AH = 11.5 # g/m3


FLOW = 1.0
STD_PRESSURE = 1e5
STD_TEMPERATURE = 20

REPETITIONS = 1

# Flushing inputs
PROPANE_FLUSH_CONC = 10000
CO2_FLUSH_CONC = 10000
FLUSH_TIME_MIN = 5


COOL_TIME_MIN = 90
HEAT_TIME_MIN = 60

COOLING_RATE = 6. # degC/min
HEATING_RATE = 3. # degC/min

PROPANE_CONCS_PRE_POST= [7875, 4200, 1470, 0]

PROPANE_CONCS = [0, 7875, 4200, 1470]
CO2_CONCS = [0, 5000, 2500, 400]
PROPANE_CONCS_CROSS = PROPANE_CONCS
CO2_CONCS_CROSS = [5000, 400]

P_STEPS = [1.2e5, 1e5, 0.8e5]


with SensiLabSetup(config_project= r'C:\work\SVN\SensiLab\chemical\configs\project\chemical_chimaera_config_project.ini',
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

    # Set up Zila reference
    # converter = CurrentLoopConverter(0.0, 17000, ConcentrationSignal, "C3H8", unit="ppm")
    # YoctoRx(DummyPlatform(setup), 'RX420MA1-27388C', 1, converter).connect()
  
    pressure_controller.set_pressure(STD_PRESSURE, wait_until_stable=False)
    espec.start()
    setup.wait(1)
    espec.set_temperature(STD_TEMPERATURE)
    setup.wait(1)

    if MEASURE_SENSORS:
        pilatus = []
        for _ip, _settings in IP_ADDRESSES.items():
            pilatus.append(PilatusTcProfilesCarassoC4_1b00(
                    setup,
                    ip_address=_ip,
                    active_mask=ACTIVE_MASK,
                    otp_version=OTP_VERSION,
                    voltage_heater=VOLTAGE_HEATER,
                    open_loop=False,
                    continuous=CONTINUOUS,
                    n_avg=N_AVG,
                    path_power_calib=_settings['PathPowerCalib']
            ))
            pilatus[-1].set_profile(
                t_set_degc=PROFILE,
                step_wait_time_ms=STEP_WAIT_TIME_MS,
                heat_ctrl_cfg=HEAT_CTRL_CFG
            )

    # ─────────────────────────────
    # GMS mmnt sequence
    #─────────────────────────────



    #Pre-Mmnt room T room temperature measurement
    setup.start_measurement_series('TestMmnt1')

    espec.set_temperature(STD_TEMPERATURE)
    gms.set_gas_mix(dict(Propane=0 * 1e-6, CO2=0*1e-6, AH=STD_AH), flow=FLOW,
                    ignore_min_flow=True, ignore_humidity_range=True)

    pilatus_tc_profile_measure_every_during(setup, pilatus, PROFILE, 5, 2, WAIT_TIME_TJ_SEC)



    espec.stop()
