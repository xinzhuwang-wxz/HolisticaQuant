import React, { useRef } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'

type MagneticButtonProps = {
  children: React.ReactNode
  className?: string
  strength?: number // how much to move towards the cursor
  tilt?: number // max tilt in degrees
}

/**
 * MagneticButton — adds magnetic cursor pull and subtle 3D tilt.
 * Wrap CTA或卡片，获得“磁性”与“指针倾斜”效果。
 */
const MagneticButton: React.FC<MagneticButtonProps> = ({ children, className, strength = 0.25, tilt = 10 }) => {
  const ref = useRef<HTMLDivElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const rX = useMotionValue(0)
  const rY = useMotionValue(0)

  const springX = useSpring(x, { stiffness: 300, damping: 25, mass: 0.8 })
  const springY = useSpring(y, { stiffness: 300, damping: 25, mass: 0.8 })
  const springRX = useSpring(rX, { stiffness: 250, damping: 20 })
  const springRY = useSpring(rY, { stiffness: 250, damping: 20 })

  const handleMouseMove: React.MouseEventHandler<HTMLDivElement> = (e) => {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const relX = e.clientX - rect.left - rect.width / 2
    const relY = e.clientY - rect.top - rect.height / 2
    const nx = relX / (rect.width / 2)
    const ny = relY / (rect.height / 2)
    x.set(relX * strength)
    y.set(relY * strength)
    rX.set(-ny * tilt)
    rY.set(nx * tilt)
  }

  const handleMouseLeave = () => {
    x.set(0); y.set(0); rX.set(0); rY.set(0)
  }

  return (
    <motion.div
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        x: springX,
        y: springY,
        rotateX: springRX,
        rotateY: springRY,
        transformStyle: 'preserve-3d',
        perspective: 800,
      }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

export default MagneticButton