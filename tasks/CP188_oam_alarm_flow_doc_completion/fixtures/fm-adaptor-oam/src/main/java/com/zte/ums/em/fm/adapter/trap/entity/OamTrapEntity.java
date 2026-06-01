package com.zte.ums.em.fm.adapter.trap.entity;

/**
 * OamTrapEntity - Per-NE trap ordering state.
 * Tracks the expected next trap ID for each OAM network element
 * to detect and handle out-of-order trap messages.
 */
public class OamTrapEntity {

    /** Composite key: neName + "_" + neType */
    private String workId;

    /** The next expected trap ID for this NE */
    private int expectedId;

    /** Maximum trap ID seen during a jump/gap event */
    private int maxJumpId;

    /** Number of ordering gaps detected for this NE */
    private int jumpCount;

    /** Timestamp of last trap received */
    private long lastTrapTime;

    public OamTrapEntity(String workId, int initialExpectedId) {
        this.workId = workId;
        this.expectedId = initialExpectedId;
        this.maxJumpId = 0;
        this.jumpCount = 0;
        this.lastTrapTime = System.currentTimeMillis();
    }

    public String getWorkId() { return workId; }
    public int getExpectedId() { return expectedId; }
    public void setExpectedId(int expectedId) { this.expectedId = expectedId; }
    public int getMaxJumpId() { return maxJumpId; }
    public void setMaxJumpId(int maxJumpId) { this.maxJumpId = maxJumpId; }
    public int getJumpCount() { return jumpCount; }
    public void incrementJumpCount() { this.jumpCount++; }
    public long getLastTrapTime() { return lastTrapTime; }
    public void setLastTrapTime(long lastTrapTime) { this.lastTrapTime = lastTrapTime; }

    /**
     * Resets the trap entity state, typically after NE restart detection.
     */
    public void reset(int newExpectedId) {
        this.expectedId = newExpectedId;
        this.maxJumpId = 0;
        this.jumpCount = 0;
        this.lastTrapTime = System.currentTimeMillis();
    }
}
