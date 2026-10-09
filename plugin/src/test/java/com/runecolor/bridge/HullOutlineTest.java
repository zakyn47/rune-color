package com.runecolor.bridge;

import org.junit.Test;

import java.awt.Point;
import java.awt.Polygon;
import java.awt.Rectangle;
import java.awt.geom.Ellipse2D;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

public class HullOutlineTest {
    private static final Point ORIGIN = new Point(180, 30);

    private static boolean has(List<int[]> outline, int x, int y) {
        return outline.stream().anyMatch(p -> p[0] == x && p[1] == y);
    }

    @Test
    public void aRectangleBecomesItsCornersOnScreen() {
        List<int[]> outline = HullOutline.of(new Rectangle(290, 180, 20, 40), ORIGIN);
        assertEquals(4, outline.size());
        assertTrue(has(outline, 470, 210));
        assertTrue(has(outline, 490, 210));
        assertTrue(has(outline, 490, 250));
        assertTrue(has(outline, 470, 250));
    }

    @Test
    public void aRoundShapeIsCappedAndStaysInBounds() {
        List<int[]> outline = HullOutline.of(new Ellipse2D.Double(0, 0, 300, 200), ORIGIN);
        assertTrue(outline.size() >= 3);
        assertTrue(outline.size() <= HullOutline.MAX_POINTS);
        for (int[] p : outline) {
            assertTrue(p[0] >= 180 && p[0] <= 480);
            assertTrue(p[1] >= 30 && p[1] <= 230);
        }
    }

    @Test
    public void nothingToOutlineGivesNull() {
        assertNull(HullOutline.of(null, ORIGIN));
        assertNull(HullOutline.of(new Rectangle(5, 5, 0, 0), ORIGIN));
        assertNull(HullOutline.of(new Rectangle(5, 5, 10, 10), null));
    }

    @Test
    public void aManyVertexPolygonIsTrimmedToMaxPoints() {
        int vertices = 21;
        int radius = 100;
        int[] xPoints = new int[vertices];
        int[] yPoints = new int[vertices];
        for (int i = 0; i < vertices; i++) {
            double angle = 2.0 * Math.PI * i / vertices;
            xPoints[i] = (int) Math.round(200 + radius * Math.cos(angle));
            yPoints[i] = (int) Math.round(200 + radius * Math.sin(angle));
        }
        Polygon polygon = new Polygon(xPoints, yPoints, vertices);
        List<int[]> outline = HullOutline.of(polygon, ORIGIN);

        assertEquals(HullOutline.MAX_POINTS, outline.size());

        Set<String> pointSet = new HashSet<>();
        for (int[] p : outline) {
            pointSet.add(p[0] + "," + p[1]);
        }
        assertEquals(HullOutline.MAX_POINTS, pointSet.size());
    }
}
