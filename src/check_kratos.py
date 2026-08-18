import platform
import sys

print("=" * 64)
print("SLOPE-MPM / KRATOS ENVIRONMENT CHECK")
print("=" * 64)

print(f"Python   : {sys.version.split()[0]}")
print(f"Machine  : {platform.machine()}")
print(f"Platform : {platform.platform()}")
print()

try:
    import KratosMultiphysics as KM
    print("KratosMultiphysics core     : PASS")
except Exception as exc:
    print("KratosMultiphysics core     : FAIL")
    print(exc)
    raise

try:
    import KratosMultiphysics.LinearSolversApplication
    print("LinearSolversApplication    : PASS")
except Exception as exc:
    print("LinearSolversApplication    : FAIL")
    print(exc)
    raise

try:
    import KratosMultiphysics.MPMApplication as MPM
    print("MPMApplication              : PASS")
except Exception as exc:
    print("MPMApplication              : FAIL")
    print(exc)
    raise

print()
print("=" * 64)
print("KRATOS MPM NATIVE INSTALLATION: PASS")
print("=" * 64)
