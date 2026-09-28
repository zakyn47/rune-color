package com.runecolor.bridge;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Properties;

/** Prepares a script profile for import into the running client. */
final class ProfileFiles {
    static final String WINDOW_BOUNDS_KEY = "runelite.clientBounds";

    private ProfileFiles() {
    }

    /**
     * Copy a profile to a temporary file carrying the client's current window bounds.
     *
     * <p>RuneLite re-applies the window bounds of the profile it switches to, and one
     * without any falls back to its game size, shrinking the window. Script profiles
     * are committed without bounds, so the client's own are carried over and the
     * window stays exactly as the user left it.
     *
     * @param source the committed profile
     * @param bounds the active profile's {@code clientBounds}, or null if it has none
     * @return a temporary file for the caller to delete once imported
     */
    static File withWindowBounds(File source, String bounds) throws IOException {
        Properties props = new Properties();
        try (InputStream in = new FileInputStream(source)) {
            props.load(in);
        }
        props.remove(WINDOW_BOUNDS_KEY);
        if (bounds != null) {
            props.setProperty(WINDOW_BOUNDS_KEY, bounds);
        }
        File merged = File.createTempFile("runecolor-profile-", ".properties");
        try (OutputStream out = new FileOutputStream(merged)) {
            props.store(out, null);
        }
        return merged;
    }
}
