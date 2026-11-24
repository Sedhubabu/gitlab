import { useState } from 'react'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  return (
      <div>
        <h1>
          Create the new gitlab
          {count}
        </h1>
        <button onClick={() => {
          setCount(count + 1)
        }}>
          click
        </button>
      </div>
  )
}

export default App
