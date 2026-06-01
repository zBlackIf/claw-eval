# OAM Alarm Processing Complete Flow Documentation

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Core Processing Flow](#2-core-processing-flow)
3. [Layer-by-Layer Module Details](#3-layer-by-layer-module-details)
4. [Typical Scenarios](#4-typical-scenarios)
5. [Core Data Structures and Decision Summary](#5-core-data-structures-and-decision-summary)

---

## 1. Architecture Overview

```
+-------------------------------------------------------------------------+
|                    OAM Alarm Processing System Architecture              |
+-------------------------------------------------------------------------+

  OAM Network Element
       |
       v  SNMP Trap (UDP)
+----------------------------------------------------------------------+
|                      EMS Alarm Collection System                       |
|                                                                       |
|  +-------------+    +--------------+    +----------------------+      |
|  | SnmpTrap    |--->| singleMonitor|--->|  receiveTrap()       |      |
|  | Listener    |    | single-thread|    |  parse + OID mapping |      |
|  +-------------+    | queuing      |    +----------+-----------+      |
|                     +--------------+               |                  |
|                                     +--------------+----------+       |
|                                     |                         |       |
|                            +--------v-------+       +---------v------+|
|                            | noticeExecutor |       | eventExecutors ||
|                            | notification   |       | per-NE bound   ||
|                            | direct report  |       | worker pool    ||
|                            +--------+-------+       +---------+------+|
|                                     |                         |       |
|                                     v                         v       |
|                            +------------------+    +----------------+ |
|                            | AlarmDelegate    |    | isOamTrapAlarm?| |
|                            | delegateAlarmData|    +--------+-------+ |
|                            +--------+---------+             |         |
|                                     |              +--------v-------+ |
|                                     |              | processOamTrap | |
|                                     |              | AlarmService   | |
|                                     |              +--------+-------+ |
|                                     |                       |         |
|                                     v                       v         |
|                            +-----------------------------------+      |
|                            |  MessageSendUtil.send2kafka()     |      |
|                            +-----------------------------------+      |
+----------------------------------------------------------------------+
```

---

## 2. Core Processing Flow

### 2.1 Entry: SNMP Trap Reception

```
OAM NE          SnmpTrapListener    singleMonitor    receiveTrap
  |                    |                  |                |
  |  SNMP Trap PDU    |                  |                |
  |------------------>|                  |                |
  |                   |   submit task    |                |
  |                   |----------------->|                |
  |                   |                  |  dequeue       |
  |                   |                  |--------------->|
  |                   |                  |                |  parse PDU
  |                   |                  |                |  OID mapping
  |                   |                  |                |  create SnmpAlarmData
  |                   |                  |                |
```

### 2.2 Thread Dispatch

```
receiveTrap        FmAlarmService       noticeExecutor    eventExecutors
     |                  |                     |                |
     |  alarmProcess()  |                     |                |
     |----------------->|                     |                |
     |                  |  check alarm type   |                |
     |                  |--+                  |                |
     |                  |  |                  |                |
     |                  |  | notification?    |                |
     |                  |  +----------------->|                |
     |                  |  |                  |  directReport  |
     |                  |  |                  |                |
     |                  |  | event alarm?     |                |
     |                  |  +---------------------------------->|
     |                  |                     |                | per-NE queue
     |                  |                     |                |
```

**Final Reporting:**
```
MessageSendUtil.send2kafka(messageType, mqMsg, meId, topicName, isNotification)
```
Alarm messages are sent to upper-layer alarm service via Kafka message queue.

---

## 3. Layer-by-Layer Module Details

### 3.1 Layer 1: Trap Reception and Queuing

```
  OAM NE       SNMP Stack     SnmpTrapListener     singleMonitor
     |             |                |                   |
     |  Trap PDU   |                |                   |
     |------------>|                |                   |
     |             |   TrapEvent    |                   |
     |             |--------------->|                   |
     |             |                |  counter++        |
     |             |                |----------+        |
     |             |                |          |        |
     |             |                |  submit  |        |
     |             |                |----------------->|
     |             |                |                   |  queuing...
     |             |                |                   |
```

**Key Points:**
- UDP transport, possible out-of-order delivery
- singleMonitor single-thread queuing ensures order from entry point

### 3.2 Layer 2: SNMP Parsing and OID Mapping

```
singleMonitor      receiveTrap()          XML Config       Return Object
      |                |                       |             |
      |                |                       |             |
      |--------------->|                       |             |
      |                |                       |             |
      |                |  1. verify version    |             |
      |                |----------+            |             |
      |                |          |            |             |
      |                |  2. extract OID       |             |
      |                |----------+            |             |
      |                |          |            |             |
      |                |  3. OID mapping       |             |
      |                |---------------------->|             |
      |                |                       |  MibField[] |
      |                |<----------------------|             |
      |                |                       |             |
      |                |  4. wrap SnmpAlarmData              |
      |                |----------------------------------->|
      |                |<-----------------------------------|
      |                |                       |             |
```

**OID Mapping Example:**

| Original OID | Mapped Property | Example Value |
|---|---|---|
| .1.3.6.1.4.1.3902.4101.1.1.2 | sendNotificationId | "1" |
| .1.3.6.1.4.1.3902.4101.1.3.1.1 | alarmId | "ALARM-001" |
| .1.3.6.1.4.1.3902.4101.1.3.1.6 | alarmPerceivedSeverity | "critical" |
| .1.3.6.1.4.1.3902.4101.1.3.1.3 | alarmType | "equipmentAlarm" |

### 3.3 Layer 3: AlarmDelegate Core Processing

<!-- TODO: This section needs to be completed based on the AlarmDelegate source code -->
<!-- Document the delegateAlarmData() method flow and parseAndSendMsg() logic -->

### 3.4 Layer 4: OAM Trap Ordering (processOamTrapAlarm)

<!-- TODO: This section needs to be completed based on FmAlarmService source code -->
<!-- Document the trap ID ordering mechanism and delay queue handling -->

---

## 4. Typical Scenarios

### 4.1 Normal Sequential Alarm Scenario

<!-- TODO: Complete this section with a sequence diagram showing normal alarm flow -->

### 4.2 Out-of-Order Trap Scenario

<!-- TODO: Complete this section showing how out-of-order traps are handled -->
<!-- Include the delay queue mechanism and expectedId tracking -->

---

## 5. Core Data Structures and Decision Summary

### 5.1 Core Data Structures

| Data Structure | Key Fields | Purpose |
|---|---|---|
| **SnmpAlarmData** | `type` alarm type, `alarmId`, `neName`, `alarmPerceivedSeverity` | Alarm data carrier from SNMP parsing |
| **OamTrapEntity** | `expectedId`, `maxJumpId`, `jumpCount` | Per-NE trap ordering state |

<!-- TODO: Complete with DelayClearAlarm and TrapEvent structures -->

### 5.2 Core Decision Points

<!-- TODO: Document the key decision points in the alarm processing flow -->
<!-- Include: notification vs event routing, OAM vs non-OAM branching, ordering decisions -->
