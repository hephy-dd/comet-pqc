---
layout: default
title: MOS
parent: Analysis Functions
nav_order: 12
---

# Metal Oxide Capacitor

Extract flatband voltage, oxide thickness and charge density.

Type: `mos`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
|`cut_param`| `float` | `0.02` | cut on 1st derivative to id voltage regions |
|`min_r_value`| `float` | `0.4` | |

## Limits

| Name | Type | Description |
|------|------|-------------|
|`v_fb1` | `float` | flatband voltage via inflection (V) |
|`v_fb2` | `float` | flatband voltage via intersection (V) |
|`c_acc` | | |
|`c_inv` | | |
|`t_ox` | `float` | oxide thickness (um) |
|`n_ox` | `float` | oxide charge density (cm^-2) |
|`a_acc` | | |
|`b_acc` | | |
|`v_acc` | | |
|`a_dep` | | |
|`b_dep` | | |
|`v_dep` | | |
|`a_inv` | | |
|`b_inv` | | |
|`v_inv` | | |
|`spl_dev` | | |
