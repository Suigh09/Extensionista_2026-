import { useEffect } from 'react'

export function usePageMotion(page: string) {
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    let context: { revert: () => void } | undefined
    let active = true
    void import('gsap').then(({ gsap }) => {
      if (!active) return
      context = gsap.context(() => {
        gsap.fromTo('.page-content > *', { autoAlpha: 0, y: 14 }, {
          autoAlpha: 1, y: 0, duration: 0.38, stagger: 0.045,
          ease: 'power2.out', clearProps: 'all',
        })
      })
    })
    return () => { active = false; context?.revert() }
  }, [page])
}
