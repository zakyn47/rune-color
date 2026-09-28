package com.runecolor.bridge;

import java.util.Objects;

/** The profile the bot wants, as stated in its reply to a snapshot. */
public final class ProfileRequest {
    public final String name;
    public final String path;

    ProfileRequest(String name, String path) {
        this.name = name;
        this.path = path;
    }

    boolean isComplete() {
        return name != null && path != null;
    }

    @Override
    public boolean equals(Object other) {
        if (!(other instanceof ProfileRequest)) {
            return false;
        }
        ProfileRequest that = (ProfileRequest) other;
        return Objects.equals(name, that.name) && Objects.equals(path, that.path);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, path);
    }
}
