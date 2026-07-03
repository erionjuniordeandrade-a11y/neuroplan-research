cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(NeuroPlan)

# --- Extension meta ---------------------------------------------------------
set(EXTENSION_NAME NeuroPlan)
set(EXTENSION_HOMEPAGE "https://example.org/NeuroPlan")
set(EXTENSION_CATEGORY "Research")
set(EXTENSION_CONTRIBUTORS "NeuroPlan contributors")
set(EXTENSION_DESCRIPTION
  "Offline, research-only guided workflow for preoperative planning of \
superficial supratentorial lesions. Not a medical device. Not for clinical or \
intraoperative use. All outputs require review by a licensed neurosurgeon.")
set(EXTENSION_ICONURL "")
set(EXTENSION_SCREENSHOTURLS "")
set(EXTENSION_DEPENDS "NA")

find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

add_subdirectory(NeuroPlanWorkflow)

include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
