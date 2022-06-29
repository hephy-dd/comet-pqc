---
layout: default
title: CV
parent: Analysis Functions
nav_order: 11
---
# Diode CV

Extract depletion voltage and resistivity.

Type: `cv`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
|`area` | `float` | `1.56e-6` | implant size in [m^2] - defaults to quarter |
|`carrier` | `str` | `electrons` | majority charge carriers, values: `holes`, `electrons` |
|`cut_param` | `float` | `0.008` | cut on 1st derivative to id voltage regions |
|`savgol_windowsize` | `int` | `null` | number of points to calculate the derivative, needs to be odd |
|`min_correl` | `float` | `0.1` | minimum correlation coefficient to say that it worked |

## Limits

| Name | Type | Description |
|------|------|-------------|
|`v_dep1` | `float` | full depletion voltage via inflection |
|`v_dep2` | `float` | full depletion voltage via intersection |
|`rho` | `float` | resistivity |
|`conc` | `float` | bulk doping concentration |
|`a_rise` | | |
|`b_rise` | | |
|`v_rise` | | |
|`a_const` | | |
|`b_const` | | |
|`v_const` | | |
|`spl_dev` | | |
