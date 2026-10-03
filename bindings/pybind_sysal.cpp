#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "sysal/serialization/serialization.hpp"
#include "sysal/sysal.hpp"

#include <algorithm>
#include <array>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace py = pybind11;

namespace
{

    sysal::Collect flags_for_scope(const std::string &scope)
    {
        using sysal::Collect;

        if(scope == "default")
        {
            return Collect::Platform | Collect::Cpu | Collect::Memory | Collect::Accelerator | Collect::Network |
                   Collect::Storage | Collect::Pci | Collect::Software | Collect::Execution | Collect::Sensors | Collect::StorageHealth;
        }
        if(scope == "basic")
        {
            return sysal::basic;
        }
        if(scope == "full")
        {
            return sysal::full;
        }

        throw py::value_error("scope must be one of: default, basic, full");
    }

    sysal::Collect flags_for_sections(const std::string &scope, const std::vector<std::string> &sections)
    {
        auto flags = flags_for_scope(scope);
        if(sections.empty())
            return flags;
        flags = sysal::Collect::Platform; // The card header always includes the host identity.
        using sysal::Collect;
        static constexpr std::array<std::pair<std::string_view, Collect>, 11> section_flags{{
            {"system", Collect::Platform | Collect::Pci},
            {"cpu", Collect::Cpu | Collect::Execution},
            {"memory", Collect::Memory | Collect::Execution | Collect::Cpu | Collect::Pci},
            {"accelerators", Collect::Accelerator | Collect::Execution | Collect::Cpu | Collect::Pci},
            {"network", Collect::Network | Collect::Execution | Collect::Cpu},
            {"storage", Collect::Storage | Collect::StorageHealth},
            {"sensors", Collect::Sensors},
            {"health", Collect::Sensors | Collect::Memory | Collect::Storage | Collect::Pci | Collect::StorageHealth},
            {"topology", Collect::Cpu | Collect::Memory | Collect::Network | Collect::Storage | Collect::Pci},
            {"software", Collect::Software},
            {"execution", Collect::Execution | Collect::Cpu | Collect::Accelerator},
        }};
        for(const auto &section : sections)
        {
            const auto entry = std::find_if(section_flags.begin(), section_flags.end(),
                                            [&](const auto &item) { return item.first == section; });
            if(entry == section_flags.end())
                throw py::value_error("unknown collection section: " + section);
            flags = flags | entry->second;
        }
        if(scope == "full")
            flags = flags | Collect::Raw;
        return flags;
    }

    py::dict collect(const std::string &scope, const std::vector<std::string> &sections)
    {
        try
        {
            const auto system = sysal::System::collect(flags_for_sections(scope, sections));
            const auto json = sysal::to_json(system, {.include_raw = false, .include_meta = true});
            return py::module_::import("json").attr("loads")(json).cast<py::dict>();
        }
        catch(const sysal::SysalError &error)
        {
            throw std::runtime_error(error.what());
        }
    }

} // namespace

PYBIND11_MODULE(_native, module)
{
    module.doc() = "Thin SystemCard adapter over Sysal's public API.";
    module.def("collect", &collect, py::arg("scope") = "default", py::arg("sections") = std::vector<std::string>{},
               "Collect a Sysal snapshot and return JSON-compatible Python data.");
}
