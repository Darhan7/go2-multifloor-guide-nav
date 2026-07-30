# Floor-map alignment: a building-level correspondence

Floor 1 and Floor 3 were mapped in independent SLAM coordinate systems. For visualization, the shared elevator-door recess is used as a landmark and Floor 1 is transformed using ordinary geometry.

![Full 2D alignment](../../assets/images/alignment/floor_alignment_2d_overlay.png)

A 2D rigid transform applies rotation and translation:

```text
p_target = R · p_source + t
```

The current engineering alignment keeps scale at 1.0, rotates Floor 1 about 16.5 degrees clockwise, and translates the elevator landmarks together. No generative method is used.

One point determines translation but not a survey-grade rotation or scale. Corridor direction and equal map resolution provide additional assumptions, so the result is suitable for building visualization and topology—not precise metrology.

![Elevator detail](../../assets/images/alignment/floor_alignment_2d_elevator_zoom.png)

Each floor keeps its native Nav2 frame; a building transform or graph describes cross-floor relations without invalidating AMCL poses and semantic anchors.

![Exploded 3D view](../../assets/images/alignment/floor_alignment_3d_exploded.png)

The vertical spacing is schematic. More precise work would add multiple surveyed correspondences and report alignment residuals.
