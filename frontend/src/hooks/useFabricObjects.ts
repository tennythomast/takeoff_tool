import { useCallback } from 'react'
import { Canvas, Rect, Circle, FabricObject } from 'fabric'

export function useFabricObjects(canvas: Canvas | null) {
  const addRectangle = useCallback(
    (options: { left?: number; top?: number; width?: number; height?: number; fill?: string } = {}) => {
      if (!canvas) return null

      const rect = new Rect({
        left: options.left || 100,
        top: options.top || 100,
        width: options.width || 100,
        height: options.height || 100,
        fill: options.fill || '#3b82f6',
      })

      canvas.add(rect)
      canvas.renderAll()
      return rect
    },
    [canvas]
  )

  const addCircle = useCallback(
    (options: { left?: number; top?: number; radius?: number; fill?: string } = {}) => {
      if (!canvas) return null

      const circle = new Circle({
        left: options.left || 200,
        top: options.top || 200,
        radius: options.radius || 50,
        fill: options.fill || '#ef4444',
      })

      canvas.add(circle)
      canvas.renderAll()
      return circle
    },
    [canvas]
  )

  const removeObject = useCallback(
    (obj: FabricObject) => {
      if (!canvas) return

      canvas.remove(obj)
      canvas.renderAll()
    },
    [canvas]
  )

  const clearCanvas = useCallback(() => {
    if (!canvas) return

    canvas.clear()
    canvas.renderAll()
  }, [canvas])

  const getActiveObject = useCallback(() => {
    if (!canvas) return null
    return canvas.getActiveObject()
  }, [canvas])

  return {
    addRectangle,
    addCircle,
    removeObject,
    clearCanvas,
    getActiveObject,
  }
}
