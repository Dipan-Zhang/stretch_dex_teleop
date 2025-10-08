#!/usr/bin/env python3
"""
Playback script for recorded dex teleop sessions.
Loads recorded joint configurations and replays them on the robot.
"""

import numpy as np
import sys
import os
import time
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stretch_body.robot as rb
from core import teleop_parameters as dt
from utils.robot_move import RobotMove
from utils.loop_timer import LoopTimer


def load_recording(recording_file):
    """
    Load a recorded teleop session from an npz file.
    
    Args:
        recording_file: Path to the .npz recording file
        
    Returns:
        tuple: (base_move_mode, joint_configs) where joint_configs is a list of configuration dicts
    """
    if not os.path.exists(recording_file):
        raise FileNotFoundError(f"Recording file not found: {recording_file}")
    
    data = np.load(recording_file, allow_pickle=True)
    base_move_mode = str(data['base_move_mode'])
    joint_configs = data['joint_config_to_save']
    
    print(f"Loaded recording from: {recording_file}")
    print(f"Base move mode: {base_move_mode}")
    print(f"Number of configurations: {len(joint_configs)}")
    
    return base_move_mode, joint_configs


def playback_recording(recording_file, robot_speed='slow', playback_speed=1.0, 
                       loop_playback=False, starting_config=None):
    """
    Playback a recorded teleop session on the robot.
    
    Args:
        recording_file: Path to the .npz recording file
        robot_speed: Speed setting for the robot ('slow', 'fast', 'max', etc.)
        playback_speed: Multiplier for playback speed (1.0 = normal, 2.0 = 2x speed, etc.)
        loop_playback: If True, continuously loop the recording
        starting_config: Optional starting configuration. If None, uses first recorded config.
    """
    # Load the recording
    base_move_mode, joint_configs = load_recording(recording_file)
    
    if len(joint_configs) == 0:
        print("ERROR: No configurations found in recording!")
        return
    
    # Initialize the robot
    print("\nInitializing robot...")
    robot = rb.Robot()
    robot.startup()
    
    # Check robot is homed
    if not robot.is_homed():
        print("ERROR: Robot must be homed before playback")
        robot.stop()
        return
    
    # Initialize RobotMove
    robot_move = RobotMove(robot, speed=robot_speed)
    robot_move.print_settings()
    
    # Determine which joints are allowed to move based on base_move_mode
    joints_allowed_to_move = ['stretch_gripper', 'joint_arm_l0', 'joint_lift', 
                              'joint_wrist_yaw', 'joint_wrist_pitch', 'joint_wrist_roll']
    
    if base_move_mode == 'prismatic':
        joints_allowed_to_move.append('joint_mobile_base_translate_by')
    elif base_move_mode == 'rotary':
        joints_allowed_to_move.append('joint_mobile_base_rotate_by')
    else:
        print(f"WARNING: Unknown base_move_mode '{base_move_mode}', defaulting to rotary")
        base_move_mode = 'rotary'
        joints_allowed_to_move.append('joint_mobile_base_rotate_by')
    
    print(f"\nJoints that will move: {joints_allowed_to_move}")
    
    # Move to starting configuration
    if starting_config is None:
        starting_config = joint_configs[0]
    
    print("\nMoving to starting configuration...")
    robot_move.to_configuration(starting_config, joints_allowed_to_move, speed='slow')
    robot.push_command()
    robot.wait_command()
    
    # Reset base odometry if using rotary mode
    if base_move_mode == 'rotary':
        print("Resetting base odometry...")
        robot.base.reset_odometry()
    
    # Playback loop
    loop_timer = LoopTimer()
    playback_count = 0
    
    try:
        while True:
            playback_count += 1
            print(f"\n{'='*60}")
            print(f"Starting playback #{playback_count}")
            print(f"{'='*60}\n")
            
            # Play through all configurations
            for i, config in enumerate(joint_configs):
                loop_timer.start_of_iteration()
                
                # Send configuration to robot
                robot_move.to_configuration(config, joints_allowed_to_move)
                robot.push_command()
                
                # Print progress
                if (i + 1) % 10 == 0 or i == 0:
                    print(f"Progress: {i+1}/{len(joint_configs)} configurations sent")
                
                loop_timer.end_of_iteration()
                
                # Sleep to control playback speed
                # Adjust sleep time based on playback_speed
                sleep_time = 0.03 / playback_speed  # Original loop ran at ~30Hz
                time.sleep(sleep_time)
            
            print(f"\nPlayback #{playback_count} complete!")
            print(f"Sent {len(joint_configs)} configurations")
            
            # If not looping, break
            if not loop_playback:
                break
            
            print("\nLooping playback (Ctrl+C to stop)...")
            time.sleep(1.0)  # Pause between loops
            
    except KeyboardInterrupt:
        print("\n\nPlayback interrupted by user")
    finally:
        print("\nStopping robot...")
        robot.stop()
        print("Playback complete!")


def main():
    parser = argparse.ArgumentParser(
        description='Playback recorded dex teleop sessions on Stretch robot'
    )
    parser.add_argument('-o', '--recording_file', type=str, 
                       help='Path to the .npz recording file')
    parser.add_argument('-s', '--speed', type=str, default='slow',
                       choices=['default', 'slow', 'fast', 'max', 'fastest_stretch_2', 'fastest_stretch_3'],
                       help='Robot speed setting (default: slow)')
    parser.add_argument('-p', '--playback_speed', type=float, default=1.0,
                       help='Playback speed multiplier (default: 1.0 = normal speed)')
    parser.add_argument('-l', '--loop', action='store_true',
                       help='Loop the playback continuously')
    parser.add_argument('-g', '--ground', action='store_true',
                       help='Use ground-level starting configuration')
    
    args = parser.parse_args()
    
    # Validate playback speed
    if args.playback_speed <= 0:
        print("ERROR: Playback speed must be positive")
        return
    
    # Get starting configuration (optional - will use first recorded config if not specified)
    starting_config = None
    if args.ground:
        lift_middle = dt.get_lift_middle(manipulate_on_ground=True)
        starting_config = dt.get_starting_configuration(lift_middle)
    
    # Run playback
    playback_recording(
        args.recording_file,
        robot_speed=args.speed,
        playback_speed=args.playback_speed,
        loop_playback=args.loop,
        starting_config=starting_config
    )


if __name__ == '__main__':
    main()
