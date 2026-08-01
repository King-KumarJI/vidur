import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProjectProvider } from './context/ProjectContext'
import { AIReasoningPage } from './pages/AIReasoningPage'
import { DashboardPage } from './pages/DashboardPage'
import { DeepLearningVisionPage } from './pages/DeepLearningVisionPage'
import { FeatureFlagsPage } from './pages/FeatureFlagsPage'
import { InspectionPage } from './pages/InspectionPage'
import { MLPredictionPage } from './pages/MLPredictionPage'
import { MemoryPage } from './pages/MemoryPage'
import { NLPPage } from './pages/NLPPage'
import { ProjectsPage } from './pages/ProjectsPage'

function App() {
  return (
    <ProjectProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route path="projects" element={<ProjectsPage />} />
            <Route path="inspection" element={<InspectionPage />} />
            <Route path="ai-reasoning" element={<AIReasoningPage />} />
            <Route path="nlp" element={<NLPPage />} />
            <Route path="ml-prediction" element={<MLPredictionPage />} />
            <Route path="deep-learning-vision" element={<DeepLearningVisionPage />} />
            <Route path="memory" element={<MemoryPage />} />
            <Route path="settings" element={<FeatureFlagsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ProjectProvider>
  )
}

export default App
