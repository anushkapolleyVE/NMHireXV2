
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
/*
  Your backend requires X-User-Id for:
  - creating a job
  - screening a job
  - fetching candidates

  For now we read it from localStorage.
  Later we can connect this to your login properly.
*/
const getUserId = () => {
  return localStorage.getItem("userId");
};

const getHeaders = () => {
  const token = localStorage.getItem("accessToken");

  return token
    ? {
        "Authorization": `Bearer ${token}`,
      }
    : {};
};

const getErrorMessage = async (response, fallback) => {
  try {
    const data = await response.json();

    if (typeof data === "string") {
      return data;
    }

    return (
      data?.detail ||
      data?.message ||
      data?.error ||
      fallback
    );
  } catch {
    return fallback;
  }
};


// --------------------------------------------------
// CREATE JOB FROM FILE
// --------------------------------------------------

export const createJob = async (file) => {
  const formData = new FormData();

  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/jobs`, {
    method: "POST",
    headers: getHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Failed to create job from file."
      )
    );
  }

  return response.json();
};


// --------------------------------------------------
// CREATE JOB FROM PASTED TEXT
// --------------------------------------------------

export const createJobFromText = async (jdText) => {
  const formData = new FormData();

  formData.append("jd_text", jdText);

  const response = await fetch(`${API_BASE_URL}/jobs`, {
    method: "POST",
    headers: getHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Failed to create job from text."
      )
    );
  }

  return response.json();
};


// --------------------------------------------------
// SCREEN JOB
// --------------------------------------------------

export const screenJob = async (jobId) => {
  const response = await fetch(
    `${API_BASE_URL}/jobs/${jobId}/screen`,
    {
      method: "POST",
      headers: getHeaders(),
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Failed to screen candidates."
      )
    );
  }

  return response.json();
};


// --------------------------------------------------
// GET USER JOBS
// --------------------------------------------------

export const getUserJobs = async () => {
  const response = await fetch(
    `${API_BASE_URL}/user/jobs`,
    {
      method: "GET",
      headers: getHeaders(),
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Failed to fetch jobs."
      )
    );
  }

  return response.json();
};


// --------------------------------------------------
// GET CANDIDATES FOR JOB
// --------------------------------------------------

export const getJobCandidates = async (jobId) => {
  const response = await fetch(
    `${API_BASE_URL}/user/jobs/${jobId}/candidates`,
    {
      method: "GET",
      headers: getHeaders(),
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Failed to fetch candidates."
      )
    );
  }

  return response.json();
};

// --------------------------------------------------
// SYNC CANDIDATES
// --------------------------------------------------

export const syncCandidates = async (source, pathOrUrl) => {
  const response = await fetch(`${API_BASE_URL}/resumes/ingest`, {
    method: "POST",
    headers: {
      ...getHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      source: source,
      path_or_url: pathOrUrl,
    }),
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Failed to sync candidates."
      )
    );
  }

  return response.json();
};

// --------------------------------------------------
// GET USER DASHBOARD
// --------------------------------------------------

export const getUserDashboard = async () => {
  const response = await fetch(
    `${API_BASE_URL}/user/dashboard`,
    {
      method: "GET",
      headers: getHeaders(),
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Failed to fetch dashboard data."
      )
    );
  }

  return response.json();
};

export const markCandidateContacted = async (jobId, candidateId) => {
  const res = await fetch(`${API_BASE_URL}/user/jobs/${jobId}/candidates/${candidateId}/contact`, {
    method: 'POST',
    headers: getHeaders()
  });
  if (!res.ok) throw new Error('Failed to mark contacted');
  return await res.json();
};

export const getAllCandidates = async () => {
  const res = await fetch(`${API_BASE_URL}/user/candidates`, {
    headers: getHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch candidates');
  return await res.json();
};

export const getOutreachData = async () => {
  const res = await fetch(`${API_BASE_URL}/user/outreach`, {
    headers: getHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch outreach data');
  return await res.json();
};

export const updateCandidateStatus = async (jobId, candidateId, status, targetPhone = null) => {
  const res = await fetch(`${API_BASE_URL}/user/jobs/${jobId}/candidates/${candidateId}/status`, {
    method: 'POST',
    headers: {
      ...getHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status, target_phone: targetPhone })
  });
  if (!res.ok) throw new Error('Failed to update candidate status');
  return await res.json();
};
