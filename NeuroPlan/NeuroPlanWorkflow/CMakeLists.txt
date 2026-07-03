set(MODULE_NAME NeuroPlanWorkflow)

set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  __init__.py
  deid_gate.py
  registration_quality.py
  )

set(MODULE_PYTHON_RESOURCES
  )

slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  )
