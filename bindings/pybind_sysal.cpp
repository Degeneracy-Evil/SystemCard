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

    sysal::Collect flags_for_scope(const std::string &scope)
    {
        using sysal::Collect;

        if(scope == "default")
        {
            return Collect::Platform | Collect::Cpu | Collect::Memory | Collect::Accelerator | Collect::Network |
                   Collect::Storage | Collect::Pci | Collect::Software | Collect::Execution;
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
        for(const auto &section : sections)
        {
            if(section == "system")
                flags = flags | Collect::Platform;
            else if(section == "cpu")
                flags = flags | Collect::Cpu | Collect::Execution;
            else if(section == "memory")
                flags = flags | Collect::Memory | Collect::Execution;
            else if(section == "accelerators")
                flags = flags | Collect::Accelerator | Collect::Execution | Collect::Pci;
            else if(section == "network")
                flags = flags | Collect::Network | Collect::Execution;
            else if(section == "storage")
                flags = flags | Collect::Storage;
            else if(section == "software")
                flags = flags | Collect::Software;
            else if(section == "execution")
                flags = flags | Collect::Execution | Collect::Cpu | Collect::Accelerator;
            else
                throw py::value_error("unknown collection section: " + section);
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
