# This file is part of MyPaint.
# Copyright (C) 2012 by Andrew Chadwick <andrewc-git@piffle.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


"""Axis-aligned planar slice of an HSV color cube, and a depth slider.
"""

from gui import gtk2compat
import gtk
from gtk import gdk
from gettext import gettext as _

from util import *
from lib.color import *
from adjbases import ColorAdjusterWidget
from adjbases import ColorAdjuster
from adjbases import SliderColorAdjuster
from adjbases import IconRenderableColorAdjusterWidget
from adjbases import HueSaturationWheelMixin
from combined import CombinedAdjusterPage
from uimisc import *
import cairo

class HSVCubeAltPage (CombinedAdjusterPage):
    """Slice+depth view through an HSV cube: page for `CombinedAdjuster`.

    The page includes a button for tumbling the cube, i.e. changing which of
    the color components the slice and the depth slider refer to.

    """

    # Tooltip mappings, indexed by whatever the slider currently represents
    _slider_tooltip_map = dict(h=_("HSV Hue"),
                               s=_("HSV Saturation"),
                               v=_("HSV Value"))
    _slice_tooltip_map = dict(h=_("HSV Saturation and Value"),
                              s=_("HSV Hue and Value"),
                              v=_("HSV Hue and Saturation"))

    def __init__(self):
        self._faces = ['h', 's', 'v']
        #table = gtk.Table(rows=2, columns=2)

        #xopts = gtk.FILL | gtk.EXPAND
        #yopts = gtk.FILL | gtk.EXPAND

        #button = borderless_button(
        #    stock_id=gtk.STOCK_REFRESH,
        #    size=gtk.ICON_SIZE_MENU,
        #    tooltip=_("Rotate cube (show different axes)")
        #)
        #button.connect("clicked", lambda *a: self.tumble())
        self.__slice = HSVCubeSlice(self)
        self.__slider = HSVCubeSlider(self)

        s_align = gtk.Alignment(xalign=0.5, yalign=0.5, xscale=0.1, yscale=0.1)
        s_align.add(self.__slice)
        self.__slider.add(s_align)

        #table.attach(s_align,      0, 1, 0, 1, gtk.FILL, yopts, 3, 3)
        #table.attach(button,       0, 1, 1, 2, gtk.FILL, gtk.FILL, 3, 3)
        #table.attach(self.__slice, 1, 2, 0, 2, xopts, yopts, 3, 3)
        self.__table = self.__slider
        self._update_tooltips()

    @classmethod
    def get_page_icon_name(self):
        return 'mypaint-tool-hsvcube'

    @classmethod
    def get_page_title(self):
        return _('HSV Cube')

    @classmethod
    def get_page_description(self):
        return _("An HSV cube which can be rotated to show different "
                 "planar slices.")

    def get_page_widget(self):
        return self.__table

    def tumble(self):
        f0 = self._faces.pop(0)
        self._faces.append(f0)
        self.__slider.queue_draw()
        self.__slice.queue_draw()
        self._update_tooltips()

    def _update_tooltips(self):
        f0 = self._faces[0]
        self.__slice.set_tooltip_text(self._slice_tooltip_map[f0])
        self.__slider.set_tooltip_text(self._slider_tooltip_map[f0])

    def set_color_manager(self, manager):
        ColorAdjuster.set_color_manager(self, manager)
        self.__slider.set_color_manager(manager)
        self.__slice.set_color_manager(manager)


class HSVCubeSlider (HueSaturationWheelMixin,
                     IconRenderableColorAdjusterWidget):
    """Concrete base class for hue/saturation wheels, indep. of color space.
    """

    """Depth of the planar slice of a cube.
    """

    vertical = True
    samples = 4

    def __init__(self, cube):
        IconRenderableColorAdjusterWidget.__init__(self)
        w = PRIMARY_ADJUSTERS_MIN_WIDTH
        h = PRIMARY_ADJUSTERS_MIN_HEIGHT
        self.set_size_request(w, h)
        self.__cube = cube

    def get_pos_for_color(self, col):
        nr, ntheta = self.get_normalized_polar_pos_for_color(col)
        mgr = self.get_color_manager()
        if mgr:
            ntheta = mgr.distort_hue(ntheta)
        nr **= 1.0/self.SAT_GAMMA
        alloc = self.get_allocation()
        wd, ht = alloc.width, alloc.height
        radius = self.get_radius(wd, ht, self.BORDER_WIDTH)
        cx, cy = self.get_center(wd, ht)
        r = radius * clamp(nr, 0, 1)
        t = clamp(ntheta, 0, 1) * 2 * math.pi
        x = int(cx + r*math.cos(t)) + 0.5
        y = int(cy + r*math.sin(t)) + 0.5
        #print(x, y, col, r)
        return x, y

    def get_color_at_position(self, x, y):
        """Gets the color at a position, for `ColorAdjusterWidget` impls.
        """
        alloc = self.get_allocation()
        cx, cy = self.get_center(alloc=alloc)
        # Normalized radius
        r = math.sqrt((x-cx)**2 + (y-cy)**2)
        radius = float(self.get_radius(alloc=alloc))
        if r > radius:
            r = radius
        r /= radius
        #r = 1
        r **= self.SAT_GAMMA
        # Normalized polar angle
        theta = 1.25 - (math.atan2(x-cx, y-cy) / (2*math.pi))
        while theta <= 0:
            theta += 1.0
        theta %= 1.0
        mgr = self.get_color_manager()
        if mgr:
            theta = mgr.undistort_hue(theta)
        return self.color_at_normalized_polar_pos(r, theta)

    def get_normalized_polar_pos_for_color(self, col):
        col = HSVColor(color=col)
        return col.s, col.h

    def color_at_normalized_polar_pos(self, r, theta):
        col = HSVColor(color=self.get_managed_color())
        #if r > 0.90:
        col.h = theta
        #col.s = 1.0
        #print(col, r, theta)
        return col

    def get_background_validity(self):
        col = HSVColor(color=self.get_managed_color())
        f0, f1, f2 = self.__cube._faces
        #return f0, getattr(col, f1), getattr(col, f2)
        return f0

    def render_background_cb(self, cr, wd, ht, icon_border=None):
        """Renders the offscreen bg, for `ColorAdjusterWidget` impls.
        """
        cr.save()

        ref_grey = self.color_at_normalized_polar_pos(0, 0)

        border = icon_border
        if border is None:
            border = self.BORDER_WIDTH
        radius = self.get_radius(wd, ht, border)

        steps = self.HUE_SLICES
        sat_slices = self.SAT_SLICES
        sat_gamma = self.SAT_GAMMA

        # Move to the centre
        cx, cy = self.get_center(wd, ht)
        cr.translate(cx, cy)

        # Clip, for a slight speedup
        cr.arc(0, 0, radius+border, 0, 2*math.pi)
        cr.clip()

        # Tangoesque outer border
        cr.set_line_width(self.OUTLINE_WIDTH)
        cr.arc(0, 0, radius, 0, 2*math.pi)
        cr.set_source_rgba(*self.OUTLINE_RGBA)
        cr.stroke()

        # Each slice in turn
        cr.save()
        cr.set_line_width(1.0)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        step_angle = 2.0*math.pi/steps
        mgr = self.get_color_manager()

        for ih in xrange(steps+1):  # overshoot by 1, no solid bit for final
            h = float(ih)/steps
            if mgr:
                h = mgr.undistort_hue(h)
            edge_col = self.color_at_normalized_polar_pos(1.0, h)
            edge_col.s = 1.0
            edge_col.v = 1.0
            rgb = edge_col.get_rgb()
            
            if ih > 0:
                # Backwards gradient
                cr.arc_negative(0, 0, radius, 0, -step_angle)
                x, y = cr.get_current_point()
                cr.line_to(0, 0)
                cr.close_path()
                lg = cairo.LinearGradient(radius, 0, float(x+radius)/2, y)
                lg.add_color_stop_rgba(0, rgb[0], rgb[1], rgb[2], 1.0)
                lg.add_color_stop_rgba(1, rgb[0], rgb[1], rgb[2], 0.0)
                cr.set_source(lg)
                cr.fill()
            
            if ih < steps:
                # Forward solid
                cr.arc(0, 0, radius, 0, step_angle)
                x, y = cr.get_current_point()
                cr.line_to(0, 0)
                cr.close_path()
                cr.set_source_rgb(*rgb)
                cr.stroke_preserve()
                cr.fill()
            cr.rotate(step_angle)
            
        cr.restore()

        # Cheeky approximation of the right desaturation gradients
        #rg = cairo.RadialGradient(0, 0, 0, 0, 0, radius)
        #add_distance_fade_stops(rg, ref_grey.get_rgb(),
        #                        nstops=sat_slices,
        #                        gamma=1.0/sat_gamma)
        #cr.set_source(rg)
        #cr.arc(0, 0, radius, 0, 2*math.pi)
        #cr.fill()

        # Tangoesque inner border
        cr.set_source_rgba(*self.EDGE_HIGHLIGHT_RGBA)
        cr.set_line_width(self.EDGE_HIGHLIGHT_WIDTH)
        cr.arc(0, 0, radius, 0, 2*math.pi)
        cr.stroke()

        cr.set_line_width(self.OUTLINE_WIDTH)
        cr.arc(0, 0, radius*0.9, 0, 2*math.pi)
        cr.set_source_rgba(0,0,0,1)
        cr.set_operator(cairo.OPERATOR_DEST_OUT)
        cr.fill()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgba(*self.OUTLINE_RGBA)
        cr.stroke()

        cr.set_source_rgba(*self.EDGE_HIGHLIGHT_RGBA)
        cr.set_line_width(self.EDGE_HIGHLIGHT_WIDTH)
        cr.arc(0, 0, radius*0.9, 0, 2*math.pi)
        cr.stroke()


        # Some small notches on the disc edge for pure colors
        """
        if wd > 75 or ht > 75:
            cr.save()
            cr.arc(0, 0, radius+self.EDGE_HIGHLIGHT_WIDTH, 0, 2*math.pi)
            cr.clip()
            pure_cols = [
                RGBColor(1, 0, 0), RGBColor(1, 1, 0), RGBColor(0, 1, 0),
                RGBColor(0, 1, 1), RGBColor(0, 0, 1), RGBColor(1, 0, 1),
            ]
            for col in pure_cols:
                x, y = self.get_pos_for_color(col)
                x = int(x)-cx
                y = int(y)-cy
                cr.set_source_rgba(*self.EDGE_HIGHLIGHT_RGBA)
                cr.arc(x+0.5, y+0.5, 1.0+self.EDGE_HIGHLIGHT_WIDTH, 0, 2*math.pi)
                cr.fill()
                cr.set_source_rgba(*self.OUTLINE_RGBA)
                cr.arc(x+0.5, y+0.5, self.EDGE_HIGHLIGHT_WIDTH, 0, 2*math.pi)
                cr.fill()
            cr.restore()

        cr.restore()
        """

    def paint_foreground_cb(self, cr, wd, ht):
        """Fg marker painting, for `ColorAdjusterWidget` impls.
        """
        col = HSVColor(color=self.get_managed_color())
        col.s = 1.0
        radius = self.get_radius(wd, ht, self.BORDER_WIDTH)
        cx = int(wd/2)
        cy = int(ht/2)
        cr.arc(cx, cy, radius+0.5, 0, 2*math.pi)
        cr.clip()
        x, y = self.get_pos_for_color(col)
        col.s = 0.9
        ex, ey = self.get_pos_for_color(col)

        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_width(5)
        cr.move_to(x, y)
        cr.line_to(ex, ey)
        cr.set_source_rgb(0, 0, 0)
        cr.stroke_preserve()

        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(3.5)
        cr.stroke_preserve()

        cr.set_source_rgb(*col.get_rgb())
        cr.set_line_width(0.25)
        cr.stroke()


class HSVCubeSlice (IconRenderableColorAdjusterWidget):
    """Planar slice through an HSV cube.
    """

    def __init__(self, cube):
        ColorAdjusterWidget.__init__(self)
        w = PRIMARY_ADJUSTERS_MIN_WIDTH
        h = PRIMARY_ADJUSTERS_MIN_HEIGHT
        self.set_size_request(w, h)
        self.__cube = cube
        self.connect('button-press-event', self.stop_fallthrough)

    def stop_fallthrough(self, widget, event):
        return True

    def __get_faces(self):
        f1 = self.__cube._faces[1]
        f2 = self.__cube._faces[2]
        if f2 == 'h':
            f1, f2 = f2, f1
        return f1, f2

    def render_background_cb(self, cr, wd, ht, icon_border=None):
        col = HSVColor(color=self.get_managed_color())
        b = icon_border
        if b is None:
            b = self.BORDER_WIDTH
        eff_wd = int(wd - 2*b)
        eff_ht = int(ht - 2*b)
        f1, f2 = self.__get_faces()

        step = max(1, int(float(eff_wd)/128))

        rect_x, rect_y = int(b)+0.5, int(b)+0.5
        rect_w, rect_h = int(eff_wd)-1, int(eff_ht)-1

        # Paint the central area offscreen
        cr.push_group()
        for x in xrange(0, eff_wd, step):
            amt = float(x)/eff_wd
            amt = 1.0 - amt
            setattr(col, f1, amt)
            setattr(col, f2, 1.0)
            lg = cairo.LinearGradient(b+x, b, b+x, b+eff_ht)
            lg.add_color_stop_rgb(*([0.0] + list(col.get_rgb())))
            setattr(col, f2, 0.0)
            lg.add_color_stop_rgb(*([1.0] + list(col.get_rgb())))
            cr.rectangle(b+x, b, step, eff_ht)
            cr.set_source(lg)
            cr.fill()
        slice_patt = cr.pop_group()

        # Tango-like outline
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.rectangle(rect_x, rect_y, rect_w, rect_h)
        cr.set_line_width(self.OUTLINE_WIDTH)
        cr.set_source_rgba(*self.OUTLINE_RGBA)
        cr.stroke()

        # The main area
        cr.set_source(slice_patt)
        cr.paint()

        # Tango-like highlight over the top
        cr.rectangle(rect_x, rect_y, rect_w, rect_h)
        cr.set_line_width(self.EDGE_HIGHLIGHT_WIDTH)
        cr.set_source_rgba(*self.EDGE_HIGHLIGHT_RGBA)
        cr.stroke()

    def get_background_validity(self):
        col = HSVColor(color=self.get_managed_color())
        f0 = self.__cube._faces[0]
        return f0, getattr(col, f0)

    def get_color_at_position(self, x, y):
        alloc = self.get_allocation()
        b = self.BORDER_WIDTH
        wd = alloc.width
        ht = alloc.height
        eff_wd = wd - 2*b
        eff_ht = ht - 2*b
        f1_amt = clamp((x-b) / eff_wd, 0, 1)
        f2_amt = clamp((y-b) / eff_ht, 0, 1)
        col = HSVColor(color=self.get_managed_color())
        f1, f2 = self.__get_faces()
        f1_amt = 1.0 - f1_amt
        f2_amt = 1.0 - f2_amt
        setattr(col, f1, f1_amt)
        setattr(col, f2, f2_amt)
        return col

    def get_position_for_color(self, col):
        col = HSVColor(color=col)
        f1, f2 = self.__get_faces()
        f1_amt = getattr(col, f1)
        f2_amt = getattr(col, f2)
        f1_amt = 1.0 - f1_amt
        f2_amt = 1.0 - f2_amt
        alloc = self.get_allocation()
        b = self.BORDER_WIDTH
        wd = alloc.width
        ht = alloc.height
        eff_wd = wd - 2*b
        eff_ht = ht - 2*b
        x = b + f1_amt*eff_wd
        y = b + f2_amt*eff_ht
        return x, y

    def paint_foreground_cb(self, cr, wd, ht):
        x, y = self.get_position_for_color(self.get_managed_color())
        draw_marker_circle(cr, x, y)


if __name__ == '__main__':
    import os
    import sys
    from adjbases import ColorManager
    mgr = ColorManager(prefs={}, datapath='.')
    cube = HSVCubePage()
    cube.set_color_manager(mgr)
    mgr.set_color(RGBColor(0.3, 0.6, 0.7))
    if len(sys.argv) > 1:
        slice = HSVCubeSlice(cube)
        slice.set_color_manager(mgr)
        icon_name = cube.get_page_icon_name()
        for dir_name in sys.argv[1:]:
            slice.save_icon_tree(dir_name, icon_name)
    else:
        # Interactive test
        window = gtk.Window()
        window.add(cube.get_page_widget())
        window.set_title(os.path.basename(sys.argv[0]))
        window.connect("destroy", lambda *a: gtk.main_quit())
        window.show_all()
        gtk.main()
