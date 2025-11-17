import { useEffect, useRef, useState } from 'react'
import { Canvas } from 'fabric'

export interface UseFabricCanvasOptions {
  width?: number
  height?: number
  backgroundColor?: string
}

export function useFabricCanvas(options: UseFabricCanvasOptions = {}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [fabricCanvas, setFabricCanvas] = useState<Canvas | null>(null)
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    if (!canvasRef.current) return

    const canvas = new Canvas(canvasRef.current, {
      width: options.width || 800,
      height: options.height || 600,
      backgroundColor: options.backgroundColor || '#ffffff',
    })

    setFabricCanvas(canvas)
    setIsReady(true)

    return () => {
      canvas.dispose()
      setFabricCanvas(null)
      setIsReady(false)
    }
  }, [options.width, options.height, options.backgroundColor])

  return {
    canvasRef,
    fabricCanvas,
    isReady,
  }
}
