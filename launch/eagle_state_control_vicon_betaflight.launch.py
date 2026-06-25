from ament_index_python.packages import \
    get_package_share_directory  # type:ignore

from launch.actions import (DeclareLaunchArgument, ExecuteProcess, GroupAction,
                            IncludeLaunchDescription)

from launch.substitutions import (LaunchConfiguration, PathJoinSubstitution,
                                  PythonExpression, TextSubstitution)
from launch_ros.actions import ComposableNodeContainer, Node  # type:ignore
from launch_ros.descriptions import ComposableNode  # type:ignore
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch import LaunchDescription  # type:ignore


def generate_launch_description():
    launch_args = [
        DeclareLaunchArgument("platform_type", default_value="eagle"),
        DeclareLaunchArgument("quad_name", default_value="eagle11"),

        DeclareLaunchArgument("pi_serial_device", default_value="/dev/ttyTHS1"),
        DeclareLaunchArgument("pi_baud", default_value="921600"),
        DeclareLaunchArgument("pi_rx_rate_hz", default_value="1000.0"),
        DeclareLaunchArgument("pi_tx_rate_hz", default_value="500.0"),
        DeclareLaunchArgument("pi_beta_states_rate_hz", default_value="500.0"),
        DeclareLaunchArgument("pi_onboard_control_rate_hz", default_value="500.0"),
        # TODO: Need to change this variable name to something else
        DeclareLaunchArgument("control_type", default_value="trpy"),  # so3 | trpy | ftau
    ]

    # acp
    platform_type = LaunchConfiguration("platform_type")
    quad_name = LaunchConfiguration("quad_name")

    # Betaflight
    pi_serial_device = LaunchConfiguration("pi_serial_device")
    pi_baud = LaunchConfiguration("pi_baud")
    pi_rx_rate_hz = LaunchConfiguration("pi_rx_rate_hz")
    pi_tx_rate_hz = LaunchConfiguration("pi_tx_rate_hz")
    pi_beta_states_rate_hz = LaunchConfiguration("pi_beta_states_rate_hz")
    pi_onboard_control_rate_hz = LaunchConfiguration("pi_onboard_control_rate_hz")
    control_type = LaunchConfiguration("control_type")

    control_config = PathJoinSubstitution(
        [
            get_package_share_directory("acp_autonomy"),
            TextSubstitution(text="config"),
            platform_type,
            TextSubstitution(text="default"),
            TextSubstitution(text="dq_control.yaml"),
        ]
    )

    nmpc_control_node = ComposableNode(
        package="dq_cpp",
        plugin="dq_nmpc_control_nodelet::NMPCControlNodelet",
        namespace=quad_name,
        name="dq_nmpc_control_nodelet",
        parameters=[control_config,
                    {'quadrotor_name': quad_name}],
        remappings=[
            ('~/odom', 'odom'),
            ('~/position_cmd', 'position_cmd'),
            ('~/trpy_cmd', 'trpy_cmd'),
            ('~/motors', 'motors'),
            ('~/predicted_path', 'predicted_path'),
            ('~/reference_path', 'reference_path'),
            ('~/imu', 'imu'),
        ],
        extra_arguments=[{'use_intra_process_comms': True}],
    )

    tracker_manager_node = ComposableNode(
        package="trackers_manager",
        plugin="trackers_manager::TrackersManager",
        namespace=quad_name,
        name="trackers_manager_node",
        parameters=[control_config],
        remappings=[("cmd", "position_cmd"), ("odom", "odom")],
        extra_arguments=[{"use_intra_process_comms": True}],
    )

    mav_service_node = ComposableNode(
        package="mav_manager",
        plugin="mav_manager::MAVManager",
        namespace=quad_name,
        name="mav_manager_service_node",
        parameters=[
            control_config,
        ],
        remappings=[
            ("odom", "odom"),
        ],
        extra_arguments=[{"use_intra_process_comms": True}],
    )

    pi_bridge_node = Node(
        package="pi_ros2_interface",
        executable="pi_bridge_node_exec",
        namespace=quad_name,
        name="pi_bridge_node",
        parameters=[{
            "serial_device": pi_serial_device,
            "baud": pi_baud,
            "rx_rate_hz": pi_rx_rate_hz,
            "tx_rate_hz": pi_tx_rate_hz,
            "beta_states_rate_hz": pi_beta_states_rate_hz,
            "onboard_control_rate_hz": pi_onboard_control_rate_hz,
            "control_type": control_type,
            "quadrotor_name": quad_name,
        }, control_config],
        output="screen",
    )

    control_nmpc_container = ComposableNodeContainer(
        name="control_container",
        namespace=quad_name,
        package="rclcpp_components",
        executable="component_container_mt",
        composable_node_descriptions=[
            tracker_manager_node,
            mav_service_node,
            nmpc_control_node
        ],
        output="screen",
    )

    ld = LaunchDescription(launch_args)
    ld.add_action(control_nmpc_container)
    ld.add_action(pi_bridge_node)
    return ld