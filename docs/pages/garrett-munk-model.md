# Garrett-Munk Model

\cite{Munk1981} is a book chapter detailing the latest version of the Garrett-Munk-model. , based on the 1979 paper. The model comprises only out of a single horizontal wave number <math>k = (k_1^2 + k_2^2)^{\frac{1}{2}}</math>, as it is assumed here that internal wave energy is distributed equally in the horizontal plane. Although the spectra are computed from moored or towed instruments, the information about the stratification is taken from fitting

<math>N(z) = N_0 e^{z/b}</math>  

to a vertical profile of buoyancy frequency, with the surface-extrapolated buoyancy frequency <math>N_0</math> and the -folding scale . Munk himself uses the values <math>f = 7.3e-5 s^{-1}</math> for the Coriolis frequency at \SI{30}{\degree} latitude, <math>N_0 \approx \SI{5.2e-3}{s^{-1}} (\SI{3}{cph})</math> and <math>b \approx \SI{1.3}{km}</math>. All spectra are dependent on the radial frequency <math>\omega</math> and the vertical mode number <math>j</math>.

The spectra of vertical displacement is computed by

<math>F_\zeta(\omega,j) = b^2 N_0 N^{-1} (\omega^2 - f^2) \omega^{-2} E(\omega,j)</math>,

the horizontal velocity by

<math>F_u(\omega,j) = F_{u_1} + F_{u_2} = b^2  N_0 N (\omega^2 + f^2) \omega^{-2} E(\omega,j)</math>,

and the energy per unit mass by

<math>F_e(\omega,j) = \frac{1}{2} (F_u + N^2 F_\zeta) = b^2  N_0 N E(\omega,j).</math>

The dimensionless energy density $E(\omega,j)$ is defined as 

<math>E(\omega,j) = B(\omega) H(j) E</math>

with the dimensionless internal wave \enquote{energy parameter} $E = \SI{6.3e-5}{}$, which Munk considers surprisingly universal. 

The frequency factor $B(\omega)$ is 

<math>B(\omega) = 2\pi^{-1} f \omega^{-1} (\omega^2 - f^2)^{-\nicefrac{1}{2}},\:\mathrm{with } \int_f^{N(z)} B(\omega) d\omega = 1</math>
<nowiki>where \enquote{the factor $(\omega^2 - f^2)^{-\nicefrac{1}{2}}$ in the expression for $B(\omega)$ is a crude attempt to allow for the peak at the inertial turning frequency}.</nowiki>
<math>H(j) = \frac{(j^2= j_\ast^2)^{-1}}{\sum_1^\infty (j^2 + j_\ast^2)^{-1}},\:\mathrm{with } \sum_{j=1}^\infty H(j) = 1</math>
The parameter $j_\ast = 3$ is the mode scale number or the \enquote{number of equivalent vertical modes} \cite{Levine1997}.
