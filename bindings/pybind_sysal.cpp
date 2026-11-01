#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "sysal/serialization/serialization.hpp"
#include "sysal/sysal.hpp"

#include <stdexcept>
#include <string>
#include <vector>

namespace py = pybind11;

namespace
{
    py::dict collect(const std::vector<sysal::Collect> &domains, sysal::FilesystemQuery filesystems,
                     sysal::SensorDevices sensors)
    {
        auto flags = sysal::Collect{};
        for(const auto domain : domains)
            flags = flags | domain;
        std::string json;
        try
        {
            const py::gil_scoped_release release;
            const auto system = sysal::System::collect(flags, {filesystems, sensors});
            json = sysal::to_json(system, {.include_raw = sysal::has(flags, sysal::Collect::Raw)});
        }
        catch(const sysal::SysalError &error)
        {
            throw std::runtime_error(error.what());
        }
        return py::module_::import("json").attr("loads")(json).cast<py::dict>();
    }
} // namespace

PYBIND11_MODULE(_native, module)
{
    module.doc() = "Thin adapter over Sysal's public domain and collection APIs.";
    py::enum_<sysal::Collect>(module, "Domain")
        .value("PLATFORM", sysal::Collect::Platform)
        .value("CPU", sysal::Collect::Cpu)
        .value("MEMORY", sysal::Collect::Memory)
        .value("ACCELERATOR", sysal::Collect::Accelerator)
        .value("NETWORK", sysal::Collect::Network)
        .value("STORAGE", sysal::Collect::Storage)
        .value("PCI", sysal::Collect::Pci)
        .value("SOFTWARE", sysal::Collect::Software)
        .value("EXECUTION", sysal::Collect::Execution)
        .value("RAW", sysal::Collect::Raw)
        .value("SENSORS", sysal::Collect::Sensors)
        .value("STORAGE_HEALTH", sysal::Collect::StorageHealth);
    py::enum_<sysal::FilesystemQuery>(module, "FilesystemQuery")
        .value("NONE", sysal::FilesystemQuery::None)
        .value("LOCAL", sysal::FilesystemQuery::Local)
        .value("ALL_MOUNTED", sysal::FilesystemQuery::AllMounted);
    py::enum_<sysal::SensorDevices>(module, "SensorDevices")
        .value("ALL", sysal::SensorDevices::All)
        .value("EXCLUDE_DISPLAY", sysal::SensorDevices::ExcludeDisplay);
    module.def("collect", &collect, py::arg("domains"), py::arg("filesystems") = sysal::FilesystemQuery::Local,
               py::arg("sensors") = sysal::SensorDevices::All,
               "Collect public Sysal domains with explicit policies; RAW retains the raw evidence output.");
}
