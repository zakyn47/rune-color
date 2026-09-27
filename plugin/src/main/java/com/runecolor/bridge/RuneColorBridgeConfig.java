package com.runecolor.bridge;

import net.runelite.client.config.Config;
import net.runelite.client.config.ConfigGroup;
import net.runelite.client.config.ConfigItem;
import net.runelite.client.config.Range;

@ConfigGroup("runecolorbridge")
public interface RuneColorBridgeConfig extends Config {
    @ConfigItem(
            keyName = "port",
            name = "Port",
            description = "Local port the RuneColor bot listens on.",
            position = 1
    )
    @Range(min = 1024, max = 65535)
    default int port() {
        return 8099;
    }

    @ConfigItem(
            keyName = "ticksPerPush",
            name = "Ticks per push",
            description = "Push every Nth game tick. 1 pushes every tick.",
            position = 2
    )
    @Range(min = 1, max = 10)
    default int ticksPerPush() {
        return 1;
    }
}
