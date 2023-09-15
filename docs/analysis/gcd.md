---
layout: default
title: GCD
parent: Analysis Functions
nav_order: 14
---

# Gate Controlled Diode

Generation currents.

**Note:** since version 0.8 there are three versions of the functions available, `gcd` is an alias for `gcd_num`

Type: `gcd`, `gcd_num`, `gcd_sym`, `gcd_legacy`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
|`cut_param`| `float` | `0.01` | cut on 1st derivative to id voltage regions |
|`maxreldev`| `float` | `0.01` | maximum relative (to the abs max in the three regions) standart deviation to consider measurement as good |

## Limits

| Name | Type | Description |
|------|------|-------------|
|`i_surf` | `float` | surface generation current |
|`i_bulk` | `float` | bulk generation current |
|`i_acc` | | |
|`i_dep` | | |
|`i_inv` | | |
|`v_acc` | | |
|`v_dep` | | |
|`v_inv` | | |
|`i_acc_relstd` | | |
|`i_dep_relstd` | | |
|`i_inv_relstd` | | |
|`spl_dev` | | |
