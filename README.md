# dd2419_detector_baseline
Traffic signs detection based on a simple detector baseline for DD2419 course

# Prerequisites

- Ubuntu 18.04
- ROS Melodic
- OpenCV

# Installing
### Install ros package
```
$ catkin_create_pkg perception rospy geometry_msgs tf2_ros tf std_msgs crazyflie_driver
$ source ../devel/setup.$(basename $SHELL)
$ mkdir perception
$ git clone -b detection https://github.com/tjr16/dd2419_detector_baseline.git
$ mkdir build
```

### Install opencv <for feature detection, not implemented yet>

# Running
### Get ros node started
```
$ rosrun perception yolo_detector.py
```

### Check message information
```
$ rosmsg info perception/Sign
$ rosmsg info perception/SignArray
```
### Check rostopic 
```
$ rostopic echo sign/detected
```
The echoing information should be of type SignArray which refers to an array of the signs it is detected currently, empty if no detection found
