"""
Kinematics module for Stretch Dex Teleop.

This module provides inverse kinematics (IK) and forward kinematics (FK) 
functionality for the Stretch robot using simplified equations optimized 
with Numba for high performance.
"""

from .simple_ik import SimpleIK

__all__ = ['SimpleIK']

