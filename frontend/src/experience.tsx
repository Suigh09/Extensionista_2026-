import { useEffect, useRef, useState } from 'react'
import type { Material, WebGLRenderer } from 'three'

export default function HomeVisual() {
  const hostRef = useRef<HTMLDivElement>(null)
  const [fallback, setFallback] = useState(false)

  useEffect(() => {
    const host = hostRef.current
    if (!host || typeof WebGLRenderingContext === 'undefined') { setFallback(true); return }
    let disposed = false
    let cleanup = () => undefined
    void import('three').then((THREE) => {
      if (disposed || !hostRef.current) return
      const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      const scene = new THREE.Scene()
      const camera = new THREE.PerspectiveCamera(44, 1, 0.1, 100)
      camera.position.set(0, 0, 7)
      let renderer: WebGLRenderer
      try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' }) }
      catch { setFallback(true); return }
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
      renderer.outputColorSpace = THREE.SRGBColorSpace
      renderer.domElement.setAttribute('aria-hidden', 'true')
      host.appendChild(renderer.domElement)

      const group = new THREE.Group()
      scene.add(group)
      const core = new THREE.Mesh(new THREE.IcosahedronGeometry(1.25, 2), new THREE.MeshStandardMaterial({ color: 0x65b5e8, roughness: 0.3, metalness: 0.1, flatShading: true }))
      group.add(core)
      const orbit = new THREE.Mesh(new THREE.TorusGeometry(2.05, 0.035, 12, 96), new THREE.MeshBasicMaterial({ color: 0xb9def5, transparent: true, opacity: 0.7 }))
      orbit.rotation.set(0.9, 0.25, 0.15)
      group.add(orbit)
      const nodeMaterial = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.45 })
      const nodeGeometry = new THREE.SphereGeometry(0.18, 20, 20)
      ;[[-1.8, 1.15, 0.3], [1.9, 0.8, 0.1], [1.15, -1.65, 0.55], [-1.5, -1.35, -0.2]].forEach(([x, y, z]) => {
        const node = new THREE.Mesh(nodeGeometry, nodeMaterial); node.position.set(x, y, z); group.add(node)
      })
      scene.add(new THREE.HemisphereLight(0xffffff, 0x193a5f, 2.1))
      const light = new THREE.DirectionalLight(0xffffff, 2.5); light.position.set(3, 4, 5); scene.add(light)

      const resize = () => {
        const width = Math.max(host.clientWidth, 1), height = Math.max(host.clientHeight, 1)
        renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix()
      }
      const resizeObserver = new ResizeObserver(resize); resizeObserver.observe(host); resize()
      let pointerX = 0, pointerY = 0
      const move = (event: PointerEvent) => {
        const rect = host.getBoundingClientRect()
        pointerX = ((event.clientX - rect.left) / rect.width - 0.5) * 0.45
        pointerY = ((event.clientY - rect.top) / rect.height - 0.5) * 0.35
      }
      if (!reduceMotion && window.matchMedia('(pointer: fine)').matches) host.addEventListener('pointermove', move)
      let visible = true
      const visibilityObserver = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting }); visibilityObserver.observe(host)
      const clock = new THREE.Clock(); let frame = 0
      const render = () => {
        if (disposed) return
        if (visible && !document.hidden) {
          const elapsed = clock.getElapsedTime()
          if (!reduceMotion) group.rotation.y = elapsed * 0.16 + pointerX
          group.rotation.x += (pointerY - group.rotation.x) * 0.04
          core.rotation.z = reduceMotion ? 0.15 : elapsed * 0.08
          renderer.render(scene, camera)
        }
        frame = requestAnimationFrame(render)
      }
      render()
      cleanup = () => {
        cancelAnimationFrame(frame); resizeObserver.disconnect(); visibilityObserver.disconnect(); host.removeEventListener('pointermove', move)
        nodeGeometry.dispose(); nodeMaterial.dispose(); core.geometry.dispose(); (core.material as Material).dispose(); orbit.geometry.dispose(); (orbit.material as Material).dispose(); renderer.dispose(); renderer.domElement.remove()
      }
    }).catch(() => setFallback(true))
    return () => { disposed = true; cleanup() }
  }, [])

  return <div ref={hostRef} className={`home-visual${fallback ? ' home-visual-fallback' : ''}`} aria-hidden="true">{fallback && <span className="visual-fallback-mark">E</span>}</div>
}
