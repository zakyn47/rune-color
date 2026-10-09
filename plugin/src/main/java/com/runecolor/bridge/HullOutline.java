package com.runecolor.bridge;

import java.awt.Point;
import java.awt.Shape;
import java.awt.geom.PathIterator;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;

/**
 * Turns a clickbox into a short screen-space outline.
 *
 * <p>The bot picks its own random point inside the outline, so every click lands
 * somewhere new but always on the object. A convex hull is enough for that and keeps
 * the payload small; clickboxes can have hundreds of path points.
 */
final class HullOutline {
    static final int MAX_POINTS = 20;

    private HullOutline() {
    }

    static List<int[]> of(Shape shape, Point origin) {
        if (shape == null || origin == null) {
            return null;
        }
        List<Point> hull = convexHull(flatten(shape));
        if (hull.size() < 3) {
            return null;
        }
        int count = Math.min(hull.size(), MAX_POINTS);
        List<int[]> outline = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            Point p = hull.get(i * hull.size() / count);
            outline.add(new int[] {origin.x + p.x, origin.y + p.y});
        }
        return outline.size() < 3 ? null : outline;
    }

    private static List<Point> flatten(Shape shape) {
        List<Point> points = new ArrayList<>();
        double[] coords = new double[6];
        for (PathIterator it = shape.getPathIterator(null, 1.0); !it.isDone(); it.next()) {
            if (it.currentSegment(coords) != PathIterator.SEG_CLOSE) {
                points.add(new Point((int) Math.round(coords[0]), (int) Math.round(coords[1])));
            }
        }
        return points;
    }

    /** Andrew's monotone chain. */
    private static List<Point> convexHull(List<Point> points) {
        List<Point> sorted = new ArrayList<>(new LinkedHashSet<>(points));
        if (sorted.size() < 3) {
            return sorted;
        }
        sorted.sort(Comparator.<Point>comparingInt(p -> p.x).thenComparingInt(p -> p.y));
        List<Point> hull = new ArrayList<>();
        for (int pass = 0; pass < 2; pass++) {
            int start = hull.size();
            for (Point p : sorted) {
                while (hull.size() >= start + 2
                        && cross(hull.get(hull.size() - 2), hull.get(hull.size() - 1), p) <= 0) {
                    hull.remove(hull.size() - 1);
                }
                hull.add(p);
            }
            hull.remove(hull.size() - 1);
            Collections.reverse(sorted);
        }
        return hull;
    }

    private static long cross(Point o, Point a, Point b) {
        return (long) (a.x - o.x) * (b.y - o.y) - (long) (a.y - o.y) * (b.x - o.x);
    }
}
