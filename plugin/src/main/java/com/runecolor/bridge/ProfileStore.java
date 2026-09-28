package com.runecolor.bridge;

import java.io.File;

/** Where RuneLite profiles are read and switched, kept apart so the rules can be tested. */
public interface ProfileStore {
    /** The name of the active profile, or null if there is none. */
    String activeName();

    /** Import the file into a profile of this name and make it the active one. */
    void apply(String name, File file) throws Exception;
}
