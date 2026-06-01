#ifndef CLONE_TYPES_H
#define CLONE_TYPES_H

#include <string>
#include <vector>
#include <map>
#include <functional>
#include <memory>

#ifdef DEV_ENV
#include "logger.h"
#else
#include "SocMwLog.h"
#include "SocMwHtvCloneTypes.h"
#endif

namespace CloneManagerMw {

#ifndef DEV_ENV
#define LOG_INFO    SOC_MW_LOG_INFO
#define LOG_DEBUG   SOC_MW_LOG_DEBUG
#define LOG_WARN    SOC_MW_LOG_WARNING
#define LOG_ERROR   SOC_MW_LOG_ERR
#endif

} // namespace CloneManagerMw

#endif // CLONE_TYPES_H
