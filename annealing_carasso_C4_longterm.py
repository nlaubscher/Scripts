# -*- coding: utf-8 -*-
import logging
from sensirion_sensilab_core import SensiLabSetup
from sensirion_sensilab_chimaera_carasso_internal.platforms.pilatus_chimaera_carasso_c4_latest import (
    PilatusContinuousCarassoC4)
from sensirion_sensilab_chimaera_carasso_internal.platforms.pilatus_carasso_c4_helper_functions import (
    run_power_characterization)

logger = logging.getLogger(__name__)


# Session settings
OPERATOR = 'NLAU'
MMNT_NAME = 'CHI048_04'  # 'test' #
MEASUREMENT_SESSION = f"{MMNT_NAME}_longterm"


PILATUS_IPS = [
    "192.168.100.111",  # CHI026-029 D0
    "192.168.100.102",  # CHI026-040 D1
    "192.168.100.100",  # CHI026-057 D2

]

ACTIVE_MASK = 32 * [True]

# Sensor operation settings
# Choose True for continuous (switch-cap) mode, False for PDM mode
CONTINUOUS = False

# Measurement settings
VOLTAGE_HEATER = 4.

# T_SET_DEGC can be DUT-specific and either has the format
# T_SET_DEGC = [T_Br1, T_Br2, T_Br3, T_Br4]  # Same temperature for all DUTs
#   or the format
# T_SET_DEGC = [  # DUT-specific temperatures
#     [T_Br1_00, T_Br1_01, ..., T_Br1_31],
#     [T_Br2_00, T_Br2_01, ..., T_Br2_31],
#     [T_Br3_00, T_Br3_01, ..., T_Br3_31],
#     [T_Br4_00, T_Br4_01, ..., T_Br4_31]
# ]
# Non-heated pixels can be set to float('nan')
nan = float('nan')
T_SET_DEGC = [
    560.,
    560.,
    560.,
    560.
]

# After annealing, the path of the last power-calibration can be given. It is the folder named 'bridge_data_files'
PATH_POWER_CALIB = [
    r"L:\Chemical\MmntSetups\Chimaera\2026_10\20261027T102749Z_CHI048_01_C4_annealing_Tsens_recalib_4109\20261027T131315Z_TSensorRecalib_8_B87C\bridge_data_files", # for D0
    r"L:\Chemical\MmntSetups\Chimaera\2026_11\20261103T141629Z_CHI048_02_C4_annealing_Tsens_recalib_78FC\20261103T170902Z_TSensorRecalib_8_4C97\bridge_data_files", # for D1 and D2
    r"L:\Chemical\MmntSetups\Chimaera\2026_11\20261103T141629Z_CHI048_02_C4_annealing_Tsens_recalib_78FC\20261103T170902Z_TSensorRecalib_8_4C97\bridge_data_files", # for D1 and D2
]

# PATH_POWER_CALIB = None

# Measurement logging
EVERY_SEC = 20.             # should be sufficient for longterm mmt
DURING_MIN = 172800.        # 120 days

# Heater-controller settings (see Carasso NPD)
HEAT_CTRL_CFG = {
    'ChopFrq': 1,  # 0: 0, 1: f_adc / 256, 2: f_adc / 4, 3: f_adc / 2, Default: 1
    'FAdc': 0,  # 0: 800 kHz, 1: 400 kHz
    'NsShpFrq': 0,  # 0: 800 kHz, 1: 1600 kHz
    'N': 3  # 0: 2, 1: 4, 2: 8, 3: 16, 4: 32, 5: 64, 6: 128, 7: 256
}


def main():
    with SensiLabSetup(config_project=r'C:\work\SVN\SensiLab\chemical\configs\project\chemical_chimaera_config_project.ini',
                   logging_level=logging.INFO,
                   metadata=dict(Operator=OPERATOR)) as setup:

        setup.start_measurement_session(MEASUREMENT_SESSION)

        pilatus = [
            PilatusContinuousCarassoC4(
                setup,
                ip_address=pilatus_ip,
                active_mask=ACTIVE_MASK,
                voltage_heater=VOLTAGE_HEATER,
                path_power_calib=power_calib_path,
            )
            for pilatus_ip, power_calib_path in zip(
                PILATUS_IPS,
                PATH_POWER_CALIB
            )
        ]

        # start continuous longterm mmt
        setup.start_measurement_series(label='longterm')
        remaining_sec = 60. * DURING_MIN
        one_day_sec = 24. * 60. * 60.
        while remaining_sec > 0:
            for _pilatus in pilatus:
                _pilatus.start_continuous_measurement(
                    T_SET_DEGC, continuous=CONTINUOUS, heat_ctrl_cfg=HEAT_CTRL_CFG)
            setup.start_continuous_measurement(every_sec=EVERY_SEC)

            # wait 24h until next step
            measurement_sec = min(one_day_sec, remaining_sec)
            setup.wait(measurement_sec)
            remaining_sec -= measurement_sec

            #stop mmt before power characterization
            setup.stop_continuous_measurement()
            for _pilatus in pilatus:
                _pilatus.stop_measurement()

            #perform power characterization with standard runin 10s at 180°C
            run_power_characterization(
                setup=setup,
                pilatus_handles=pilatus,
                temperature_setpoints = [float('nan'), 80., 200., 320., 440., 560.],
            )


if __name__ == '__main__':
    main()