cmake_minimum_required(VERSION 3.28)
project(systemcard_native LANGUAGES CXX)

include(FetchContent)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)

set(SYSAL_VERSION "0.0.8" CACHE STRING "Pinned Sysal release version")
set(SYSAL_PACKAGE_URL
    "https://github.com/Degeneracy-Evil/sysal/releases/download/v${SYSAL_VERSION}/sysal-${SYSAL_VERSION}-linux-x86_64.tar.gz"
    CACHE STRING "Sysal release package URL")
set(SYSAL_PACKAGE_SHA256
    "1fd6a848990c3f72dc67d97ede6cd4aae798ae9c9f950ed8d168268dc8863f03"
    CACHE STRING "Sysal release package SHA-256")

FetchContent_Declare(
    sysal_package
    URL "${SYSAL_PACKAGE_URL}"
    URL_HASH "SHA256=${SYSAL_PACKAGE_SHA256}"
    DOWNLOAD_EXTRACT_TIMESTAMP FALSE
)
FetchContent_MakeAvailable(sysal_package)

set(SYSAL_INCLUDE_DIR "${sysal_package_SOURCE_DIR}/include")
set(SYSAL_LIBRARY "${sysal_package_SOURCE_DIR}/lib/libsysal.a")
if(NOT EXISTS "${SYSAL_INCLUDE_DIR}/sysal/sysal.hpp" OR NOT EXISTS "${SYSAL_LIBRARY}")
    message(FATAL_ERROR "The Sysal ${SYSAL_VERSION} release package has an unexpected layout")
endif()

add_library(sysal STATIC IMPORTED GLOBAL)
set_target_properties(sysal PROPERTIES IMPORTED_LOCATION "${SYSAL_LIBRARY}")

pybind11_add_module(_native MODULE bindings/pybind_sysal.cpp)
target_compile_features(_native PRIVATE cxx_std_20)
target_compile_definitions(_native PRIVATE _GLIBCXX_USE_CXX11_ABI=0)
target_include_directories(_native PRIVATE "${SYSAL_INCLUDE_DIR}")
target_link_libraries(_native PRIVATE sysal ${CMAKE_DL_LIBS})
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS 11)
        target_sources(_native PRIVATE bindings/libstdcxx_compat.cpp)
    endif()
    target_link_options(_native PRIVATE -static-libstdc++ -static-libgcc)
endif()

install(TARGETS _native LIBRARY DESTINATION systemcard)
