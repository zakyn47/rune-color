package com.runecolor.bridge;

import lombok.extern.slf4j.Slf4j;
import net.runelite.client.plugins.Plugin;
import net.runelite.client.plugins.PluginDescriptor;

@Slf4j
@PluginDescriptor(
        name = "RuneColor Bridge",
        description = "Pushes exact player vitals to the RuneColor bot over localhost.",
        enabledByDefault = false
)
public class RuneColorBridgePlugin extends Plugin {
    @Override
    protected void startUp() {
        log.info("RuneColor Bridge started.");
    }

    @Override
    protected void shutDown() {
        log.info("RuneColor Bridge stopped.");
    }
}
