# Response Fitter
v. 2024-10-11

This was written to speed up the response data assessment and to straighten up the methodics of fitting

## Usage
### Opening and Cropping Data
Click Open Data in top left - the file need to contain some `Time [unit]`, `R [unit]` columns and may contain also `Concentration [unit]` column. Other columns are ignored

By selecting some range in the plot, you can crop the data in temporal axis.

## Logic: Knees and Sections
The data can be decorated by so-called ***Knees***, which are key points where the response should be observed.
After inserting knees you can use the function **Create sections**, which creates the list of sections in between knees.
Such sections can be edited by double-clicking selected section in the Section list.
Section can be created also by using **Create section** button after selecting some part of the data.
***Sections*** are the parts of data which are fitted separately.


The recommended approach is to create sections from knees and then slightly edit them or create consequentially sections by selecting.
Beware! The sections should be created from "left to right", otherwise the order would affect the *t<sub>90</sub>* calculation

### Knees creation

For now, knees can only be edited manually as a semicolon `;` delimited list.

## Fitting
Fitting of sections is automatic just by selecting the type of fit. A good approach is to use **Fit all sections** and the show the results.
Go one section after another a try to select better ranges or better type of function to make a good fit.

## Data export

Either by button or clicking right button on table.

## *t<sub>90</sub>* notes
The calculation of *t<sub>90</sub>* works well if all fits are good and done in a sequential manner. The algorithm takes for each section the difference of fitted *y<sub>0</sub>* and *y<sub>0</sub>* fitted in preceding section.
(The first section takes the data at the very first point of section.)
After refitting some section the other sections **are not recaluclated**, som make shure, you fit the section one by one if you do some change, ideally use fit-all function if all sections can be fitted with the same type.

## Data corrections
You can **Interpolate** flaw data within the selection bound or **Filter** data within the selection bound (or all data if nothing is selected).
