# Motion Lite

- [Motion Lite](#motion-lite)
  - [Introduction](#introduction)
  - [Milestones](#milestones)
    - [Raspberry Pi Model B+](#raspberry-pi-model-b)
  - [Dependencies](#dependencies)
  - [Major Design Roadblocks and Workarounds](#major-design-roadblocks-and-workarounds)
    - [Global Interpreter Lock](#global-interpreter-lock)
      - [Localhost Streaming + IPC Solution](#localhost-streaming--ipc-solution)
      - [Separate Timeframe for Reading and Writing](#separate-timeframe-for-reading-and-writing)
    - [High Expense from AccumulateWeighted and GaussianBlur](#high-expense-from-accumulateweighted-and-gaussianblur)
    - [Memory Limitation](#memory-limitation)
  - [References](#references)

## Introduction

Like the apt package `motion`, `motion-lite` allows real-time motion detection and video capturing.
However, since `motion` is primarily meant for machines with sufficient video-processing power, single board computers like Raspberry Pi is usually unfit for its video capturing mode.
When `motion` is capturing videos, one of the four CPUs bumps to 100% while the others remain idle, and the videos are usually downgraded to 2 to 3 frames per second or less!

`motion-lite` uses a reliable, robust, but less sophisticated motion detection algorithm.
It is highly optimized for machines with very limited computing power to capture satisfactory-quality videos (on motion detection).

This project is specifically designed for raspberry pi camera mounted on a raspberry pi 3 B+ computer.
~~Nevertheless, it should not take long to port the code onto any other python 3.5 supporting platform.~~

**Updates in `v1.0`**: the project can now work on any python 3.5 supporting platform.
Anything specific to Raspbian and picamera is decoupled from the core of this project.
`basic_motion_capture` module provides the generic image processing and recording functions.
`pi_motion_capture` module extends the `basic_motion_capture` and provides `picamera` specific implementations. 

## Milestones

### Raspberry Pi Model B+

As of 1/9/2019, the average framerates (on motion detection) are:

* ~16 fps for 720 x 1280 resolution
* 8.6 fps for 1080 x 1920 resolution

## Dependencies

* OpenCV 4.0:
  * Build the source code directly (takes a long time due to poor computing power)
  * Use `pip install`
* `picamera` Module:
  * Should be native for newer pi models
  * Use `pip install`

## Major Design Roadblocks and Workarounds

### Global Interpreter Lock

C++ was the original choice of language.
Unfortunately, python module `picamera` is the official API for pi camera.
Despite the fact that the `picamera` module is written in C.
Digging into the C source code would cost me waaayy too much time and is obviously not worth it.
Therefore, python is chosen.

However, python's GIL confined the extent that the multi-threaded application could perform concurrent tasks.
Upon attempting to perform concurrent read-write, the CPU for one core is fixated at 100%, and the framerate is less than 3 fps. This is very disappointing.

There are two workarounds that I could think of:

1. Directly solve the GIL problem by using `multiprocessing` module: to have the producer process (reading the frames) stream the frames into localhost server. The localhost server then queue the received frames, and write the frames from the queue concurrently as the producer process is reading.
2. Delay the writing - only start writing when the no more motion is detected and the captured frames stopped queuing. This spread the read and write into different time frames, and the two thread will not compete for CPU resources.

#### Localhost Streaming + IPC Solution

This solution is still in conception stage and is not yet implemented.
Nevertheless, it should eventually replace the current solution if it turns out to have better performance.

A couple obvious problems are associated with this solution:

1. Serializing and deserializing numpy arrays (that represents a frame) can be expensive on both sides if high-resolution frames were to be streamed.
2. This does not solve the high computing cost (on the frame-reading thread) incurred by the AccumulateWeighted and GaussianBlur function calls.
3. To solve problem 2., one may consider networking 3 or 4 different processes. This indeed solve the high-expense on single thread problem, but it also means that one single frame may have to be streamed twice (to the video-capturing process, and to the image processing process). What's worse is that the image processing process has to continuously send the accumulate-weighted image back to the video capturing process in order to keep the reference image updated. This will incur way too much redundant computing expense.

#### Separate Timeframe for Reading and Writing

This is the currently deployed solution.
I designed a WriteLock class that allows frame-reading thread to have the priority over the video-capturing thread.
Here are the things that WriteLock does:

1. When the frame-reading thread is not detecting motions, and frames are not queued to write, the `WriteLock` permits writing to video file.
2. When the video is being captured, the `WriteLock` allows currently-working frame to be written, and then forbid further writing.
3. If the captured frames in the queue exceeds a threshold, **read override option** is enabled, this re-enables writing to occur concurrently as reading. (It will reduce performance at times, but will prevent ot of memory crashes if the threshold is carefully chosen.)
4. When the **read override option** is enabled, if the queue size is reduced to a certain lower bound, the **read override option** will be disabled again.

### High Expense from AccumulateWeighted and GaussianBlur

AccumulateWeighted and GaussianBlur are heavy-load, 'blocking' actions that significantly reduces the framerate while capturing video AND accumulating weighted image.
This roadblock is two-folded. One one aspect it reduces framerate because it's a blocking action.
On another aspect, it reduces framerate because it consumes a very high amount of CPU.

Workarounds:

1. Move these actions to another thread. Frames are queued and processed on that thread instead. While motions are not detected and video is not being captured, the frame-reading thread processes the frame, and send the processed frame to the accumulator thread (to accumulate). While the video is being captured, the raw frame is sent to the accumulator thread to be processed there. This workaround takes care of the 'blocking action' aspect of the problem.
2. Based on workaround 1, call `time.sleep(some_interval)` each time an image is accumulated. This spread the short and massive usage of CPU to a longer interval, the spared resources will be used for frame processing and thus improve the overall performance. The `some_interval` MUST be carefully chosen, otherwise the accumulator will lag, and even if there are no motion after a recording period, it will continue to detect motions until the most recent still images are all accumulated.

### Memory Limitation

Raspberry pi has reltively poor RAM size (1GB), and is prone to out-of-memory crashes.
The memory limitation, however, applies to any consumer-producer pattern that uses a queue communicate.
When consumer cannot catch up to speed with producer when the producer is constantly producing, the machine will eventually run out of memory regardless of how much memory it has.

For the video-capturing thread, if the frame-queue threshold is poorly chosen, the memory will continue to increase when motions are detected and frames are being queued (without being consumed/written).
The trick here is to do something like `time.sleep(0.01)` on the producer side, and choose a reasonable queue threshold to enable this producer-specific time sleep when the consumer cannot catch up. If the sleep interval is too long, the performnce will suffer, nd if the sleep interval is too short, the memory may run out of memory just the same.

## References

1. The original source for motion detection algorithm: [PyImageSearch](https://www.pyimagesearch.com/2015/06/01/home-surveillance-and-motion-detection-with-the-raspberry-pi-python-and-opencv/)