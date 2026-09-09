---
name: Sonic Compliance
colors:
  surface: '#f8f9ff'
  surface-dim: '#d8dae1'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3fa'
  surface-container: '#eceef5'
  surface-container-high: '#e6e8ef'
  surface-container-highest: '#e0e2e9'
  on-surface: '#181c21'
  on-surface-variant: '#424655'
  inverse-surface: '#2d3136'
  inverse-on-surface: '#eef1f7'
  outline: '#737687'
  outline-variant: '#c3c6d8'
  surface-tint: '#0053da'
  primary: '#0051d5'
  on-primary: '#ffffff'
  primary-container: '#276afa'
  on-primary-container: '#fefcff'
  inverse-primary: '#b4c5ff'
  secondary: '#006b5c'
  on-secondary: '#ffffff'
  secondary-container: '#65fade'
  on-secondary-container: '#007262'
  tertiary: '#aa2f13'
  on-tertiary: '#ffffff'
  tertiary-container: '#cd4729'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea7'
  secondary-fixed: '#65fade'
  secondary-fixed-dim: '#41ddc2'
  on-secondary-fixed: '#00201b'
  on-secondary-fixed-variant: '#005045'
  tertiary-fixed: '#ffdad2'
  tertiary-fixed-dim: '#ffb4a3'
  on-tertiary-fixed: '#3d0600'
  on-tertiary-fixed-variant: '#8c1900'
  background: '#f8f9ff'
  on-background: '#181c21'
  surface-variant: '#e0e2e9'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.05em
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
  max-width: 1280px
---

## Brand & Style
The design system is built on a **High-Contrast Modern** aesthetic that bridges the gap between rigid government compliance and the agility of consumer fintech. The visual narrative centers on "Frictionless Authority"—using high-energy colors and tech-forward layouts to make regulatory tasks feel instantaneous and empowering rather than bureaucratic.

The interface prioritizes clarity through massive whitespace, vibrant accents, and a "soft-tech" feel. It utilizes a mix of **Minimalism** for data density and **Glassmorphism** for AI-driven overlays to signify intelligence and depth. The emotional goal is to evoke a sense of momentum, security, and modern efficiency.

## Colors
This design system utilizes a "Vivid Light" palette. The **Electric Blue** primary color functions as the core brand anchor, used for key actions and structural highlights. **Fresh Teal** is reserved for secondary information and growth indicators, while **Warm Coral** acts as a high-visibility accent for primary CTAs and AI-powered insights.

The background uses a **Light Lavender/Off-white** tint to reduce eye strain compared to pure white, providing a sophisticated canvas for high-contrast elements. Gradients should be used sparingly, primarily as subtle linear transitions (45-degree angle) from Primary Blue to Secondary Teal on hero surfaces and progress indicators.

## Typography
The typographic hierarchy relies on the contrast between the sharp, contemporary geometry of **Hanken Grotesk** for headings and the systematic utility of **Inter** for functional data. 

Headlines should use tight tracking and heavy weights to command attention. Body text maintains generous line-height for readability during long compliance reviews. Label styles use a slight uppercase treatment with expanded letter spacing to differentiate metadata from actionable content.

## Layout & Spacing
The design system employs a **Fluid-Fixed Hybrid** grid. Layouts use a 12-column system on desktop and a 4-column system on mobile. To emphasize the "tech-forward" nature, content is grouped into logical "pods" or cards rather than separated by lines.

Rhythm is maintained through an 8px base unit. Heavy "outside-in" padding is used to focus the user's eye on central AI results. Components like stat tiles and charts should always have a minimum of 24px internal padding to maintain a premium, airy feel.

## Elevation & Depth
This design system uses **Ambient Shadows** and **Tonal Layering** to create a sense of organized hierarchy.

1.  **Level 0 (Base):** Off-white background (#F6F8FF).
2.  **Level 1 (Cards):** Pure white surfaces with a soft, diffused shadow (0px 10px 30px rgba(47, 111, 255, 0.08)).
3.  **Level 2 (Overlays/AI Tooltips):** Semi-transparent white (85% opacity) with a 20px backdrop-blur, creating a glassmorphic effect that signals "intelligent" live data.
4.  **Level 3 (Modals/CTAs):** High-contrast surfaces with a more pronounced shadow (0px 20px 40px rgba(0, 0, 0, 0.12)).

Avoid inner shadows or heavy borders. Use subtle 1px borders in a darker tint of the background color (#E0E6FF) only when necessary for accessibility.

## Shapes
The shape language is defined by **Extended Roundedness**. All container surfaces (cards, stat tiles) use a 20px (rounded-xl) corner radius to feel approachable and modern. 

Buttons, tags, and badges follow a **Pill-shaped** (full-round) convention to reinforce the "fintech" visual language. Interactive inputs use a slightly softer 12px radius to balance density with the overall system aesthetic.

## Components
-   **Buttons:** Primary buttons are pill-shaped with the Warm Coral background and white text. Secondary buttons use a "Ghost" style—transparent background with a 2px Electric Blue border.
-   **Stat Tiles:** High-contrast containers with large `headline-lg` numbers. Use Primary Blue for neutral stats and Secondary Teal for positive compliance trends.
-   **AI-Annotation Overlays:** Use the glassmorphic style (Backdrop blur) with a 2px "Fresh Teal" left-border to highlight specific text or fields being analyzed.
-   **Charts:** Donut and progress rings must use "Soft" ends (rounded caps). Use gradients for the active track and a light version of the primary color for the inactive track.
-   **Persistent Navigation:** A bottom-docked pill-shaped bar on mobile, and a slim, high-contrast left-rail on desktop using the Primary Blue background with white icons.
-   **Input Fields:** Large 56px height, 12px rounded corners, with a "focus" state that uses a 2px Electric Blue glow.