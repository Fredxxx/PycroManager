#include "extcode.h"
#ifdef __cplusplus
extern "C" {
#endif

/*!
 * TwoAnalog_SetVoltage
 */
void __cdecl TwoAnalog_SetVoltage(double MaxVoltage, double MinVoltage, 
	double ao0, double ao1);
/*!
 * TwoAnalog_triggerAndStaircase_pyDLL_subVI
 */
void __cdecl TwoAnalog_triggerAndStaircase_pyDLL_subVI(int32_t TTLUptime, 
	double MinVoltage, double triggerTimingMs, double MaxVoltage, double delayMs, 
	double InitialStepV, int32_t NumberOfZPlanes, double zRage);

MgErr __cdecl LVDLLStatus(char *errStr, int errStrLen, void *module);

void __cdecl SetExecuteVIsInPrivateExecutionSystem(Bool32 value);

#ifdef __cplusplus
} // extern "C"
#endif

