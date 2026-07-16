cmake_minimum_required(VERSION 3.28)
project(systemcard_native LANGUAGES CXX)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)

set(SYSAL_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/third_party/sysal/include" CACHE PATH
    "Path to Sysal public headers")
set(SYSAL_LIBRARY
    "${CMAKE_CURRENT_SOURCE_DIR}/vendor/sysal/lib/libsysal.so")

if(NOT EXISTS "${SYSAL_INCLUDE_DIR}/sysal/sysal.hpp")
    message(FATAL_ERROR "Sysal public headers are missing. Run: git submodule update --init --recursive")
endif()

if(NOT EXISTS "${SYSAL_LIBRARY}")
    message(FATAL_ERROR
        "A prebuilt Sysal library was not found at ${SYSAL_LIBRARY}. "
        "Add the supported library to vendor/sysal/lib/libsysal.so")
endif()

add_library(sysal UNKNOWN IMPORTED GLOBAL)
set_target_properties(sysal PROPERTIES IMPORTED_LOCATION "${SYSAL_LIBRARY}")

pybind11_add_module(_native MODULE bindings/pybind_sysal.cpp)
target_compile_features(_native PRIVATE cxx_std_20)
target_include_directories(_native PRIVATE "${SYSAL_INCLUDE_DIR}")
target_link_libraries(_native PRIVATE sysal ${CMAKE_DL_LIBS})
set_target_properties(_native PROPERTIES
    BUILD_RPATH "$<TARGET_FILE_DIR:sysal>"
    INSTALL_RPATH "$ORIGIN"
)

install(TARGETS _native LIBRARY DESTINATION systemcard)
install(FILES "${SYSAL_LIBRARY}" DESTINATION systemcard)
