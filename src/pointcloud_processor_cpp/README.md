# pointcloud_processor (rewrite)

Dual-thread ROS1 node using lock-free `moodycamel::ConcurrentQueue` (no mutex on hot paths).

## Threads

| Thread                | Role                                               |
| --------------------- | -------------------------------------------------- |
| ROS `AsyncSpinner(2)` | Subscribes, `try_enqueue` to ingress queue         |
| Collector             | `sleep_until` period, drain ingress, enqueue batch |
| Worker                | Dequeue, PCL filter, publish                       |

## Build

```bash
./scripts/fetch_third_party.sh   # if not using bootstrap
export BUILD_TYPE=RelWithDebInfo  # default; also Debug, Release
./scripts/build.sh
```
