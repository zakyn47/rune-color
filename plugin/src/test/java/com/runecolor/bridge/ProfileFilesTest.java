package com.runecolor.bridge;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Properties;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

public class ProfileFilesTest {
    @Rule
    public TemporaryFolder folder = new TemporaryFolder();

    private File profile(String... keyValues) throws IOException {
        Properties props = new Properties();
        for (int i = 0; i < keyValues.length; i += 2) {
            props.setProperty(keyValues[i], keyValues[i + 1]);
        }
        File file = folder.newFile();
        try (OutputStream out = new FileOutputStream(file)) {
            props.store(out, null);
        }
        return file;
    }

    private static Properties load(File file) throws IOException {
        Properties props = new Properties();
        try (InputStream in = new FileInputStream(file)) {
            props.load(in);
        }
        return props;
    }

    @Test
    public void addsTheWindowBoundsAndKeepsEverythingElse() throws IOException {
        File merged = ProfileFiles.withWindowBounds(
                profile("runelite.gameSize", "765x503"), "-8:18:1750:1073");
        Properties props = load(merged);
        assertEquals("-8:18:1750:1073", props.getProperty("runelite.clientBounds"));
        assertEquals("765x503", props.getProperty("runelite.gameSize"));
    }

    @Test
    public void replacesBoundsTheFileAlreadyHas() throws IOException {
        File merged = ProfileFiles.withWindowBounds(
                profile("runelite.clientBounds", "0:0:10:10"), "1:2:3:4");
        assertEquals("1:2:3:4", load(merged).getProperty("runelite.clientBounds"));
    }

    @Test
    public void leavesBoundsOutWhenTheClientHasNone() throws IOException {
        File merged = ProfileFiles.withWindowBounds(profile("a", "b"), null);
        assertFalse(load(merged).containsKey("runelite.clientBounds"));
    }
}
