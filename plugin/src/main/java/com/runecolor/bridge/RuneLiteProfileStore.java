package com.runecolor.bridge;

import net.runelite.client.config.ConfigManager;
import net.runelite.client.config.ConfigProfile;
import net.runelite.client.config.ProfileManager;

import java.io.File;
import java.io.FileNotFoundException;

/** Reads and switches profiles the way RuneLite's own Profiles panel does. */
public class RuneLiteProfileStore implements ProfileStore {
    private final ProfileManager profileManager;
    private final ConfigManager configManager;

    public RuneLiteProfileStore(ProfileManager profileManager, ConfigManager configManager) {
        this.profileManager = profileManager;
        this.configManager = configManager;
    }

    @Override
    public String activeName() {
        ConfigProfile profile = configManager.getProfile();
        return profile == null ? null : profile.getName();
    }

    @Override
    public void apply(String name, File file) throws Exception {
        if (!file.isFile()) {
            throw new FileNotFoundException(file.getPath());
        }
        File merged = ProfileFiles.withWindowBounds(file,
                configManager.getConfiguration("runelite", "clientBounds"));
        ConfigProfile profile;
        try (ProfileManager.Lock lock = profileManager.lock()) {
            // The repo file is the source of truth, so a stale copy of this profile
            // is replaced rather than merged into.
            ConfigProfile stale = lock.findProfile(name);
            if (stale != null) {
                lock.removeProfile(stale.getId());
                // removeProfile only unregisters it; without this, every switch
                // would leave another orphaned file in profiles2.
                ProfileManager.profileConfigFile(stale).delete();
            }
            profile = lock.createProfile(name);
            configManager.importAndMigrate(lock, merged, profile);
            lock.getProfiles().forEach(p -> p.setActive(false));
            profile.setActive(true);
            lock.dirty();
        } finally {
            merged.delete();
        }
        configManager.switchProfile(profile);
    }
}
