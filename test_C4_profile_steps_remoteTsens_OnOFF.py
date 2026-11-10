# -*- coding: utf-8 -*-
from sensirion_sensilab_core import SensiLabSetup
from sensirion_sensilab_chimaera_carasso_internal.platforms.pilatus_chimaera_carasso_c4_latest import (
    PilatusTcProfilesCarassoC4, PilatusContinuousCarassoC4)
from sensirion_sensilab_chimaera_carasso_internal.platforms.pilatus_carasso_c4_helper_functions import (
    pilatus_tc_profile_measure_every_during, run_power_characterization)



# Session settings
OPERATOR = 'NLAU'
MMNT_NR =  'CHI048_0x' #'CHI031_02' #'CHI028_01' #
MEASUREMENT_SESSION = f"{MMNT_NR}_C4_powerCycles"

PILATUS_IP = "192.168.100.100"

# Active mask: For now (bug?) set only sensors that reliably work to True
ACTIVE_MASK = 32 * [True]

# Sensor operation settings
# Choose True for continuous (switch-cap) mode, False for PDM mode
CONTINUOUS = False

# Profile: List of maximal 10 entries, corresponding to the up to 10 profile steps.
#   Each entry must be a list of the 4 pixels in degrees Celsius.
#   Use float('nan') for open-loop control without heating.
nan = float('nan')
PROFILE = [
    [nan, nan, nan, nan],
    [560., 560., nan, 560.],
    [nan, nan, nan, nan],
    [560., 560., nan, 560.],
    [nan, nan, nan, nan],
    [560., 560., nan, 560.],
    [nan, nan, nan, nan],
    [560., 560., nan, 560.],
    [nan, nan, nan, nan],
    [560., 560., nan, 560.],
]

# After annealing, the path of the last power-calibration can be given. It is the folder named 'bridge_data_files'
PATH_POWER_CALIB = r"C:\work\SensiLab\data\2026_11\20261104T102120Z_CHI048_03_C4_annealing_Tsens_recalib_38FD"  #double check path on messpc
PATH_POWER_CALIB = None

# Time to wait in milliseconds for each profile step
STEP_WAIT_TIME_MS = 100.

# Heater controller config
HEAT_CTRL_CFG = {
    'ChopFrq': 1,  # 0: 0, 1: f_adc / 256, 2: f_adc / 4, 3: f_adc / 2, Default: 1
    'FAdc': 0,  # 0: 800 kHz, 1: 400 kHz
    'NsShpFrq': 0,  # 0: 800 kHz, 1: 1600 kHz
    'N': 3  # 0: 2, 1: 4, 2: 8, 3: 16, 4: 32, 5: 64, 6: 128, 7: 256
}

# Averaging of Noise-shaper input, Decimator output and TJunction. Choose 32, 64 or 128
N_AVG = 128

# Time to wait for Tjunction measurement
WAIT_TIME_TJ_SEC = 1e-3 * N_AVG * 4

# ADC frequency during integration
f_adc = 400000. if (HEAT_CTRL_CFG['FAdc'] & 1) else 800000.
# Integration time for N_AVG measurements for 4 bridges:
t_single = 2048. * N_AVG / f_adc

# For EVERY_SEC use at least: 0.25 + len(PROFILE) * (0.015 + t_single + 0.001 * STEP_WAIT_TIME_MS)
EVERY_SEC = 0.25 + len(PROFILE) * (0.015 + t_single + 0.001 * STEP_WAIT_TIME_MS)
DURING_MIN = 1.

# Heater voltage
VOLTAGE_HEATER = 4.


def main():
    with SensiLabSetup(config_project=r'C:\work\SVN\SensiLab\chemical\configs\project\chemical_chimaera_config_project.ini',
                   logging_level=logging.INFO,
                   metadata=dict(Operator=OPERATOR)) as setup:

        setup.start_measurement_session(MEASUREMENT_SESSION)

        pilatus = PilatusTcProfilesCarassoC4(
            setup,
            ip_address=PILATUS_IP,
            active_mask=ACTIVE_MASK,
            voltage_heater=VOLTAGE_HEATER,
            continuous=CONTINUOUS,
            n_avg=N_AVG,
            path_power_calib=PATH_POWER_CALIB
        )
        pilatus.set_profile(
            t_set_degc=PROFILE,
            heat_ctrl_cfg=HEAT_CTRL_CFG,
            step_wait_time_ms=STEP_WAIT_TIME_MS
        )

        setup.start_measurement_series(label='test')

        pilatus_tc_profile_measure_every_during(setup, pilatus, PROFILE, EVERY_SEC, DURING_MIN, WAIT_TIME_TJ_SEC)

        # Pilatus object has to be destroyed, before creating a continuous measurement object
        pilatus.self_destroy()

        pilatus = PilatusContinuousCarassoC4(
            setup,
            ip_address=PILATUS_IP,
            active_mask=ACTIVE_MASK,
            voltage_heater=VOLTAGE_HEATER,
            path_power_calib=PATH_POWER_CALIB
        )

        #perform power characterization with standard runin 10s at 180°C
        run_power_characterization(
            setup=setup,
            pilatus_handles=pilatus,)
        
        # Pilatus object has to be destroyed, before creating a TC-profile measurement object
        pilatus.self_destroy()


if __name__ == '__main__':
    main()